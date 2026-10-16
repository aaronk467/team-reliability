"""Statistical monitoring. All calendar days are UTC; limits use baseline only.

I-MR constants: d2=1.128 and D4=3.267 for successive pairs. Default log
I-MR limits backtransform to minutes. Nonoverlapping beta-binomial posterior
predictive limits integrate uncertainty in baseline late risk. Signals are only points strictly outside
limits. Neither chart adjusts for case mix or unresolved dispatches.
"""
from datetime import datetime, timedelta, timezone
import math
from statistics import mean


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamps must be ISO 8601 strings with timezone offsets")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid ISO 8601 timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamps require a timezone offset")
    return dt.astimezone(timezone.utc)


def validate_records(records):
    """Validate records, returning normalized copies sorted by dispatch and ID."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a nonempty list")
    if len(records) > 100000:
        raise ValueError("at most 100000 records are supported")
    from .delay_patterns import validate_context
    result, ids = [], set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("each record must be an object")
        validate_context(row)
        clean = dict(row)
        for key in ("id", "zone", "priority"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"{key} must be a nonempty string")
            clean[key] = row[key].strip()
        if clean["id"] in ids:
            raise ValueError("record IDs must be unique")
        ids.add(clean["id"])
        dispatched = _timestamp(row.get("dispatched_at"))
        arrived = _timestamp(row.get("arrived_at"))
        if arrived < dispatched:
            raise ValueError("arrived_at must be at or after dispatched_at")
        reason = row.get("delay_reason", "")
        if reason is not None and not isinstance(reason, str):
            raise ValueError("delay_reason must be a string or null")
        clean.update(dispatched_at=dispatched.isoformat(), arrived_at=arrived.isoformat(),
                     minutes=(arrived-dispatched).total_seconds()/60, _dt=dispatched)
        result.append(clean)
    return sorted(result, key=lambda r: (r["_dt"], r["id"]))


def _summary(rows, target):
    n = len(rows)
    late = sum(r["minutes"] > target for r in rows)
    p = late/n
    z = 1.959963984540054
    denominator = 1+z*z/n
    center = (p+z*z/(2*n))/denominator
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    values = sorted(r["minutes"] for r in rows)
    # Hyndman-Fan type 7 linear interpolation (NumPy/R default).
    pos = .9*(n-1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return dict(count=n, late_count=late, late_rate=p,
                late_ci_low=max(0,center-half), late_ci_high=min(1,center+half),
                p90_minutes=values[lo]+(values[hi]-values[lo])*(pos-lo))


# The two-sided Gaussian three-sigma tail probability. Exact-binomial bounds
# preserve this nominal tail budget for KNOWN p; baseline p is estimated here.
CHART_ALPHA = math.erfc(3 / math.sqrt(2))


def _binomial_bounds(n, p, alpha=CHART_ALPHA):
    """Central discrete binomial quantiles, stable without factorial overflow.

    Recurrences start at the mode with relative mass 1 and move outwards;
    no tiny mode PMF is exponentiated. Normalizing the masses avoids an
    overflowing factorial or underflow of (1-p)**n in large bins. Quantiles
    are the smallest integer k with CDF(k)>=q. Signals strictly outside the
    returned bounds have each known-p tail probability <= alpha/2.
    """
    if p == 0:
        return 0, 0
    if p == 1:
        return n, n
    mode = min(n, math.floor((n + 1) * p))
    weights = [0.0] * (n + 1)
    weights[mode] = 1.0
    for k in range(mode, 0, -1):
        weights[k - 1] = weights[k] * k / (n - k + 1) * (1 - p) / p
    for k in range(mode, n):
        weights[k + 1] = weights[k] * (n - k) / (k + 1) * p / (1 - p)
    total = math.fsum(weights)
    lower_target, upper_target = alpha / 2 * total, (1 - alpha / 2) * total
    lower = None
    cumulative = 0.0
    for k, weight in enumerate(weights):
        cumulative += weight
        if lower is None and cumulative >= lower_target:
            lower = k
        if cumulative >= upper_target:
            return lower, k
    # Floating summation can end a few ulps below total, never materially
    # below the upper quantile target. This fallback handles that rounding.
    return lower, n



def _beta_binomial_bounds(n, a, b, alpha=CHART_ALPHA):
    """Central beta-binomial quantiles using mode-centered relative masses.

    For K|p~Binomial(n,p), p~Beta(a,b), the adjacent mass ratio is
    P(k+1)/P(k) = (n-k)/(k+1) * (k+a)/(n-k-1+b). Starting at a global
    mode avoids factorials, gamma cancellation, tiny PMFs, and overflow.
    This also handles monotone and U-shaped beta-binomial distributions.
    Each posterior-predictive tail outside the integer bounds is at most
    alpha/2, conditional on the Beta-Binomial model; this is not a claim
    of uniform frequentist false-alarm calibration for a fixed unknown p.
    """
    if a > 1 and b > 1:
        mode = min(n, max(0, math.floor((n + 1) * (a - 1) / (a + b - 2))))
    elif a <= 1 and b > 1:
        mode = 0
    elif b <= 1 and a > 1:
        mode = n
    else:
        # Both shapes <=1: largest mass is at an endpoint. Its ordering
        # follows a versus b; a=b=1 is uniform and either endpoint works.
        mode = n if a > b else 0
    weights = [0.0] * (n + 1)
    weights[mode] = 1.0
    for k in range(mode, 0, -1):
        weights[k - 1] = weights[k] * k / (n - k + 1) * (n - k + b) / (k - 1 + a)
    for k in range(mode, n):
        weights[k + 1] = weights[k] * (n - k) / (k + 1) * (k + a) / (n - k - 1 + b)
    total = math.fsum(weights)
    lower_target, upper_target = alpha / 2 * total, (1 - alpha / 2) * total
    lower = None
    cumulative = 0.0
    for k, weight in enumerate(weights):
        cumulative += weight
        if lower is None and cumulative >= lower_target:
            lower = k
        if cumulative >= upper_target:
            return lower, k
    return lower, n


def _comparison(rows, target, baseline_end):
    before = [r for r in rows if r['_dt'].date() < baseline_end]
    after = [r for r in rows if r['_dt'].date() >= baseline_end]
    b = _summary(before, target) if before else None
    m = _summary(after, target) if after else None
    return dict(baseline=b, monitoring=m,
                late_rate_delta_pp=100*(m['late_rate']-b['late_rate']) if b and m else None,
                p90_delta_minutes=m['p90_minutes']-b['p90_minutes'] if b and m else None)


def analyze(records, target_minutes=8.0, baseline_days=20, priority="all",
            imr_scale="log", aggregation_days=7, p_method="beta_binomial"):
    """Monitor completed dispatches using frozen baseline limits.

    Baseline is the first N UTC calendar days of the selected priority.
    Default I-MR estimates variation in log(minutes) and backtransforms the
    individuals center/limits into minutes; MR remains in log-ratio units.
    Log limits are unavailable if any baseline duration is zero. A later
    zero has no log-chart estimate and generates a warning, rather than an
    invented offset. Raw-minute charts are available explicitly.

    Default p charts integrate baseline risk uncertainty using a Jeffreys
    Beta(1/2,1/2) prior and frozen Beta(k+1/2,m-k+1/2) posterior, where
    k of m baseline calls are late. Limits are beta-binomial predictive
    quantiles for each future period's actual count. Baseline points fitted
    this posterior and are not evaluated as predictive signals. Optional
    exact_binomial retains the legacy plug-in chart for comparison.
    Bins are nonoverlapping and restart at the baseline/monitor boundary.
    Missing dates are not fabricated as successful/zero-demand calls.
    Comparison deltas describe observed change, not causal intervention effects.
    """
    if isinstance(target_minutes, bool) or not isinstance(target_minutes, (int,float)) or not math.isfinite(target_minutes) or target_minutes <= 0:
        raise ValueError("target_minutes must be finite and positive")
    if isinstance(baseline_days, bool) or not isinstance(baseline_days,int) or not 1 <= baseline_days <= 3650:
        raise ValueError("baseline_days must be an integer from 1 to 3650")
    if isinstance(aggregation_days, bool) or not isinstance(aggregation_days,int) or not 1 <= aggregation_days <= 365:
        raise ValueError("aggregation_days must be an integer from 1 to 365")
    if imr_scale not in ('log', 'raw'):
        raise ValueError("imr_scale must be 'log' or 'raw'")
    if not isinstance(p_method,str) or p_method not in ('beta_binomial', 'exact_binomial'):
        raise ValueError("p_method must be 'beta_binomial' or 'exact_binomial'")
    if not isinstance(priority,str) or not priority.strip():
        raise ValueError("priority must be a nonempty string")
    from .delay_patterns import summarize_delays
    rows = validate_records(records)
    if priority != "all":
        rows = [r for r in rows if r["priority"] == priority]
    if not rows:
        raise ValueError("no records match the priority filter")
    start = rows[0]["_dt"].date()
    end = start+timedelta(days=baseline_days)
    observation_end = rows[-1]['_dt'].date()
    zones = []
    groups = {}
    for row in rows:
        groups.setdefault(row['zone'], []).append(row)
    for zone, group in sorted(groups.items()):
        baseline = [r for r in group if r["_dt"].date() < end]
        warnings = []
        if len(baseline) < 20:
            warnings.append("Fewer than 20 baseline calls: limits are preliminary.")
        if imr_scale == 'log' and any(r['minutes'] == 0 for r in group):
            warnings.append("Zero-minute durations cannot be logged: affected log points and adjacent moving ranges are unavailable. Any baseline zero disables log-chart limits; verify timestamps or choose raw scale.")
        transform = (lambda value: math.log(value) if value > 0 else None) if imr_scale == 'log' else (lambda value: value)
        values = [transform(r['minutes']) for r in group]
        baseline_values = values[:len(baseline)]
        baseline_defined = bool(baseline_values) and all(v is not None for v in baseline_values)
        transformed_center = mean(baseline_values) if baseline_defined else None
        mrbar = mean(abs(baseline_values[i]-baseline_values[i-1]) for i in range(1,len(baseline_values))) if baseline_defined and len(baseline_values)>1 else None
        if mrbar == 0:
            warnings.append("Constant baseline: I-MR limits unavailable; collect variable observations.")
        if len(baseline)<2:
            warnings.append("At least two baseline calls are needed for I-MR limits.")
        valid = mrbar is not None and mrbar > 0
        if imr_scale == 'log':
            center = math.exp(transformed_center) if transformed_center is not None else None
            if valid:
                low_log, high_log = transformed_center-3*mrbar/1.128, transformed_center+3*mrbar/1.128
                # Extremely heterogeneous timestamps can overflow exp, even
                # though all observed durations are finite. Never emit inf.
                try:
                    lcl, ucl = math.exp(low_log), math.exp(high_log)
                except OverflowError:
                    valid = False
                    lcl = ucl = None
                    warnings.append("Log-chart backtransformed limits overflow: limits unavailable; review timestamp extremes.")
            else:
                lcl = ucl = None
        else:
            center = transformed_center
            lcl = max(0, center-3*mrbar/1.128) if valid else None
            ucl = center+3*mrbar/1.128 if valid else None
        mrucl = 3.267*mrbar if valid else None
        points=[]
        for i,r in enumerate(group):
            mr=abs(values[i]-values[i-1]) if i and values[i] is not None and values[i-1] is not None else None
            points.append(dict(id=r["id"],dispatched_at=r["dispatched_at"],minutes=r["minutes"],in_baseline=r["_dt"].date()<end,
                               signal=bool(valid and values[i] is not None and (r["minutes"]<lcl or r["minutes"]>ucl)), moving_range=mr,
                               mr_signal=bool(valid and mr is not None and mr>mrucl)))
        baseline_late = sum(r["minutes"]>target_minutes for r in baseline)
        p = baseline_late/len(baseline) if baseline else None
        predictive = p_method == 'beta_binomial'
        posterior_a = baseline_late + .5 if predictive and baseline else None
        posterior_b = len(baseline) - baseline_late + .5 if predictive and baseline else None
        posterior_mean = posterior_a/(posterior_a+posterior_b) if posterior_a is not None else None
        chart_center = posterior_mean if predictive else p
        if p in (0,1):
            warnings.append(
                "Baseline late proportion is 0 or 1: posterior predictive limits retain uncertainty; zero observed events does not establish zero or certain population risk."
                if predictive else
                "Baseline late proportion is 0 or 1: binomial limits degenerate. A change flags any contrary outcome, but the baseline does not establish zero or certain population risk; collect more data."
            )
        if not baseline:
            warnings.append("No baseline calls for this zone: chart limits unavailable.")
        bins = {}
        for r in group:
            day = r['_dt'].date()
            anchor = start if day < end else end
            period_start = anchor + timedelta(days=((day-anchor).days // aggregation_days)*aggregation_days)
            bins.setdefault(period_start, []).append(r)
        periods=[]
        bound_cache = {}
        for period_start, period_rows in sorted(bins.items()):
            in_baseline = period_start < end
            period_end = min(period_start+timedelta(days=aggregation_days-1), end-timedelta(days=1) if in_baseline else observation_end, observation_end)
            n=len(period_rows); late=sum(r["minutes"]>target_minutes for r in period_rows)
            if p is not None:
                if n not in bound_cache:
                    bound_cache[n] = _beta_binomial_bounds(n,posterior_a,posterior_b) if predictive else _binomial_bounds(n,p)
                low_count, high_count = bound_cache[n]
                lower, upper = low_count/n, high_count/n
            else:
                low_count = high_count = lower = upper = None
            periods.append(dict(date=period_start.isoformat(),period_start=period_start.isoformat(),period_end=period_end.isoformat(),
                                n=n,late_count=late,proportion=late/n,lcl=lower,ucl=upper,lcl_count=low_count,ucl_count=high_count,
                                in_baseline=in_baseline,signal_evaluated=bool(p is not None and (not predictive or not in_baseline)),
                                signal=bool(p is not None and (not predictive or not in_baseline) and (late<low_count or late>high_count))))
        baseline_i = sum(point["in_baseline"] and point["signal"] for point in points)
        baseline_mr = sum(point["in_baseline"] and point["mr_signal"] for point in points)
        baseline_p = sum(point["in_baseline"] and point["signal"] for point in periods)
        if baseline_i or baseline_mr or baseline_p:
            warnings.append(
                (f"Baseline may be unstable: {baseline_i} I-chart and {baseline_mr} moving-range rule-1 signals. "
                 "Baseline predictive p points are not evaluated. Review baseline conditions before interpreting frozen limits.")
                if predictive else
                (f"Baseline may be unstable: {baseline_i} I-chart, {baseline_mr} moving-range, "
                 f"and {baseline_p} p-chart rule-1 signals. Review baseline conditions before interpreting frozen limits.")
            )
        review_reasons = []
        if len(baseline) < 20:
            review_reasons.append("Fewer than 20 baseline calls.")
        if not valid:
            review_reasons.append("I-MR baseline limits unavailable.")
        if baseline_i or baseline_mr:
            review_reasons.append("Baseline I/MR signals require investigation before treating the reference as stable.")
        baseline_quality = dict(baseline_count=len(baseline), i_signals=baseline_i, mr_signals=baseline_mr,
                                p_signals=None if predictive else baseline_p, imr_limits_available=valid,
                                review_recommended=bool(review_reasons), reasons=review_reasons)
        zones.append(dict(zone=zone,**_summary(group,target_minutes),baseline_count=len(baseline),warnings=warnings,
                          comparison=_comparison(group,target_minutes,end),baseline_quality=baseline_quality,
                          delay_patterns=summarize_delays(group,target_minutes),
                          imr=dict(center=center,lcl=lcl,ucl=ucl,mr_center=mrbar,mr_ucl=mrucl,scale=imr_scale,
                                   mr_units='log ratio' if imr_scale=='log' else 'minutes',points=points),
                          p_chart=dict(center=chart_center,baseline_late_rate=p,method=p_method,alpha=CHART_ALPHA,
                                       prior_alpha=.5 if predictive else None,prior_beta=.5 if predictive else None,
                                       posterior_alpha=posterior_a,posterior_beta=posterior_b,posterior_mean=posterior_mean,
                                       baseline_signal_policy='not_evaluated_fitted_reference' if predictive else 'descriptive_diagnostic',
                                       aggregation_days=aggregation_days,points=periods)))
    return dict(summary=_summary(rows,target_minutes),comparison=_comparison(rows,target_minutes,end),
                delay_patterns=summarize_delays(rows,target_minutes),
                zones=zones,target_minutes=target_minutes,baseline_days=baseline_days,
                baseline_start=start.isoformat(),baseline_end=(end-timedelta(days=1)).isoformat(),priority=priority,
                imr_scale=imr_scale,aggregation_days=aggregation_days,p_method=p_method,
                warnings=["Observational signals prompt investigation, not causal attribution. Completed calls only; missing arrivals require separate follow-up.",
                          "Pooled priorities can confound zone comparisons: filter priority to assess case mix before operational decisions." if priority == "all" else "Priority-stratified analysis still requires review of case mix and dispatch practice.",
                          "Beta-binomial predictive limits integrate baseline-risk uncertainty under a fixed Jeffreys prior and independent common-risk Bernoulli calls. Coverage is conditional on this model, not a guaranteed fixed-risk frequentist false-alarm rate. Baseline points fit the posterior and are not predictive tests."
                          if p_method=='beta_binomial' else
                          "Exact-binomial limits use estimated baseline risk as a plug-in, not a known population probability; they omit baseline-estimation uncertainty and require independent, common-risk calls within each period.",
                          "Log I-MR reduces skew under multiplicative variation but does not guarantee lognormality, independent calls, or calibrated false-alarm rates. Multiple repeated charts increase chance signals." if imr_scale=='log' else "Raw I-MR can flag expected extremes from a skewed distribution. Multiple repeated charts increase chance signals."])
