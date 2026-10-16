"""Statistical monitoring. All calendar days are UTC; limits use baseline only.

I-MR constants: d2=1.128 and D4=3.267 for successive pairs. P charts
use pooled baseline late risk and each day's denominator. Signals are only
single points strictly outside limits. Neither chart adjusts for case mix.
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
    result, ids = [], set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("each record must be an object")
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


def analyze(records, target_minutes=8.0, baseline_days=20, priority="all"):
    """Analyze complete observed dispatches; target exceedance means strictly >.

    Baseline comprises first N UTC calendar days from earliest dispatch in the
    selected priority. Missing days are not zero-demand observations. Limits
    never use monitoring data. At least two baseline calls are needed for I-MR.
    """
    if isinstance(target_minutes, bool) or not isinstance(target_minutes, (int,float)) or not math.isfinite(target_minutes) or target_minutes <= 0:
        raise ValueError("target_minutes must be finite and positive")
    if isinstance(baseline_days, bool) or not isinstance(baseline_days,int) or not 1 <= baseline_days <= 3650:
        raise ValueError("baseline_days must be an integer from 1 to 3650")
    if not isinstance(priority,str) or not priority.strip():
        raise ValueError("priority must be a nonempty string")
    rows = validate_records(records)
    if priority != "all":
        rows = [r for r in rows if r["priority"] == priority]
    if not rows:
        raise ValueError("no records match the priority filter")
    start = rows[0]["_dt"].date()
    end = start+timedelta(days=baseline_days)
    zones = []
    for zone in sorted({r["zone"] for r in rows}):
        group = [r for r in rows if r["zone"] == zone]
        baseline = [r for r in group if r["_dt"].date() < end]
        warnings = []
        if len(baseline) < 20:
            warnings.append("Fewer than 20 baseline calls: limits are preliminary.")
        center = mean(r["minutes"] for r in baseline) if baseline else None
        mrbar = mean(abs(baseline[i]["minutes"]-baseline[i-1]["minutes"]) for i in range(1,len(baseline))) if len(baseline)>1 else None
        if mrbar == 0:
            warnings.append("Constant baseline: I-MR limits unavailable; collect variable observations.")
        if len(baseline)<2:
            warnings.append("At least two baseline calls are needed for I-MR limits.")
        valid = mrbar is not None and mrbar > 0
        lcl = max(0, center-3*mrbar/1.128) if valid else None
        ucl = center+3*mrbar/1.128 if valid else None
        mrucl = 3.267*mrbar if valid else None
        points=[]
        for i,r in enumerate(group):
            mr=abs(r["minutes"]-group[i-1]["minutes"]) if i else None
            points.append(dict(id=r["id"],dispatched_at=r["dispatched_at"],minutes=r["minutes"],in_baseline=r["_dt"].date()<end,
                               signal=bool(valid and (r["minutes"]<lcl or r["minutes"]>ucl)), moving_range=mr,
                               mr_signal=bool(valid and mr is not None and mr>mrucl)))
        p = sum(r["minutes"]>target_minutes for r in baseline)/len(baseline) if baseline else None
        if p in (0,1):
            warnings.append("Baseline late proportion is 0 or 1: p-chart limits degenerate; exact binomial methods or more baseline data are advisable.")
        if not baseline:
            warnings.append("No baseline calls for this zone: chart limits unavailable.")
        days=[]
        for day in sorted({r["_dt"].date() for r in group}):
            daily=[r for r in group if r["_dt"].date()==day]
            n=len(daily); late=sum(r["minutes"]>target_minutes for r in daily)
            se=math.sqrt(p*(1-p)/n) if p is not None else None
            lower=max(0,p-3*se) if p is not None else None
            upper=min(1,p+3*se) if p is not None else None
            days.append(dict(date=day.isoformat(),n=n,late_count=late,proportion=late/n,lcl=lower,ucl=upper,in_baseline=day<end,
                             signal=bool(p is not None and (late/n<lower or late/n>upper))))
        baseline_i = sum(point["in_baseline"] and point["signal"] for point in points)
        baseline_mr = sum(point["in_baseline"] and point["mr_signal"] for point in points)
        baseline_p = sum(point["in_baseline"] and point["signal"] for point in days)
        if baseline_i or baseline_mr or baseline_p:
            warnings.append(
                f"Baseline may be unstable: {baseline_i} I-chart, {baseline_mr} moving-range, "
                f"and {baseline_p} p-chart rule-1 signals. Review baseline conditions before interpreting frozen limits."
            )
        zones.append(dict(zone=zone,**_summary(group,target_minutes),baseline_count=len(baseline),warnings=warnings,
                          imr=dict(center=center,lcl=lcl,ucl=ucl,mr_center=mrbar,mr_ucl=mrucl,points=points),
                          p_chart=dict(center=p,points=days)))
    return dict(summary=_summary(rows,target_minutes),zones=zones,target_minutes=target_minutes,baseline_days=baseline_days,
                baseline_start=start.isoformat(),baseline_end=(end-timedelta(days=1)).isoformat(),priority=priority,
                warnings=["Observational signals prompt investigation, not causal attribution. Completed calls only; missing arrivals require separate follow-up.",
                          "Pooled priorities can confound zone comparisons: filter priority to assess case mix before operational decisions." if priority == "all" else "Priority-stratified analysis still requires review of case mix and dispatch practice.",
                          "Normal-approximation p-chart limits can be unreliable with small expected late/on-time counts; inspect Wilson intervals and denominators."])
