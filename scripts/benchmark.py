"""Reproduce a small, seeded monitoring benchmark with Python's standard library.

This is a characterization, not a release gate or a claim of clinical validity.
Run from the repository root: python scripts/benchmark.py
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import random
from statistics import mean, median
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from responsewatch import analyze  # noqa: E402

SEED = 4672026
BASELINE_DAYS = 20
MONITORING_DAYS = 25
CALLS_PER_DAY = 4
TARGET_MINUTES = 8.0
START = datetime(2026, 1, 1, tzinfo=timezone.utc)
ALPHA = math.erfc(3 / math.sqrt(2))
SCENARIOS = {"unchanged": 1.0, "slowdown_1_5x": 1.5, "improvement_0_72x": 0.72}
METHODS = ["beta_binomial", "exact_binomial"]
ROBUSTNESS = {
    "low_volume": dict(calls_per_day=1),
    "high_volume": dict(calls_per_day=12),
    "variable_volume": dict(calls_per_day=[1, 7, 3, 8, 2, 6, 4]),
    "short_baseline": dict(baseline_days=5),
    "serial_dependence": dict(rho=0.5),
}


def wilson(successes: int, total: int) -> list[float]:
    """95% interval for the Monte Carlo run-level event proportion."""
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total**2)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def row(identifier: str, dispatched: datetime, minutes: float) -> dict:
    # Match field collection's whole-second precision. No nonpositive durations.
    arrived = dispatched + timedelta(seconds=max(1, round(minutes * 60)))
    return dict(id=identifier, zone="Simulated", priority="high",
                dispatched_at=dispatched.isoformat(), arrived_at=arrived.isoformat())


def simulated_records(seed: int, ratio: float, baseline_days=BASELINE_DAYS,
                      calls_per_day=CALLS_PER_DAY, rho=0.0) -> list[dict]:
    """Stationary lognormal or stationary log-AR(1), then a fixed level shift."""
    rng = random.Random(seed)
    rows = []
    previous = rng.normalvariate(0, 0.35) if rho else None
    for day in range(baseline_days + MONITORING_DAYS):
        n = calls_per_day[day % len(calls_per_day)] if isinstance(calls_per_day, list) else calls_per_day
        for call in range(n):
            if rho:
                previous = rho * previous + math.sqrt(1 - rho**2) * rng.normalvariate(0, 0.35)
                minutes = math.exp(math.log(7.3) + previous)
            else:
                minutes = rng.lognormvariate(math.log(7.3), 0.35)
            if day >= baseline_days:
                minutes *= ratio
            rows.append(row(f"{day}-{call}", START + timedelta(days=day, seconds=round(86400 * call/n)), minutes))
    return rows


def reference_binomial_bounds(n: int, p: float) -> tuple[int, int, list[float]]:
    """Independent direct finite-sum formula, suitable for these small n.

    Production uses recurrence weights from the mode instead; sharing its helper
    here would only test the implementation against itself.
    """
    masses = [math.comb(n, k) * p**k * (1 - p)**(n - k) for k in range(n + 1)]
    cdf, lower, upper = 0.0, None, None
    for k, mass in enumerate(masses):
        cdf += mass
        if lower is None and cdf >= ALPHA / 2:
            lower = k
        if upper is None and cdf >= 1 - ALPHA / 2:
            upper = k
    assert lower is not None and upper is not None
    return lower, upper, masses


def check_binomial_known_answers() -> list[dict]:
    checks = []
    for n, p in [(4, 0.5), (10, 0.5), (28, 0.5), (28, 0.2), (100, 0.8)]:
        lower, upper, masses = reference_binomial_bounds(n, p)
        baseline = [row(f"b-{i}", START + timedelta(days=i // 5, hours=i % 5),
                        10 if i < round(100 * p) else 4) for i in range(100)]
        # Probe boundary counts and their immediate outside neighbors.
        probes = sorted({k for k in [lower - 1, lower, upper, upper + 1] if 0 <= k <= n})
        for late_count in probes:
            monitored = [row(f"m-{i}", START + timedelta(days=20, seconds=i),
                             10 if i < late_count else 4) for i in range(n)]
            result = analyze(baseline + monitored, target_minutes=TARGET_MINUTES,
                             baseline_days=BASELINE_DAYS, priority="high", aggregation_days=7,
                             p_method="exact_binomial")
            point = next(p for p in result["zones"][0]["p_chart"]["points"] if not p["in_baseline"])
            assert (point["lcl_count"], point["ucl_count"]) == (lower, upper)
            assert point["signal"] == (late_count < lower or late_count > upper)
        checks.append(dict(n=n, p=p, lcl_count=lower, ucl_count=upper,
                           strict_lower_tail=math.fsum(masses[:lower]),
                           strict_upper_tail=math.fsum(masses[upper + 1:]),
                           checked_counts=probes))
    assert checks[1]["lcl_count"] == 1 and checks[1]["ucl_count"] == 9
    assert math.isclose(checks[1]["strict_upper_tail"], 1 / 1024)
    return checks


def check_predictive_known_answers() -> list[dict]:
    """Check production against independent beta-function finite PMFs."""
    from responsewatch.stats import _beta_binomial_bounds
    checks = []
    # Uniform predictive PMF; Jeffreys no-data boundary; then actual posteriors
    # including all-on-time, all-late, balanced, and asymmetric baselines.
    for n, a, b in [(1000, 1.0, 1.0), (20, .5, .5), (28, .5, 80.5),
                    (28, 80.5, .5), (28, 40.5, 40.5), (100, 3.5, 17.5)]:
        beta_log = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        masses = [math.comb(n, k) * math.exp(math.lgamma(k+a) + math.lgamma(n-k+b)
                  - math.lgamma(n+a+b) - beta_log) for k in range(n+1)]
        total = math.fsum(masses)
        assert math.isclose(total, 1, rel_tol=1e-9, abs_tol=1e-9)
        masses = [m/total for m in masses]
        cdf, lower, upper = 0.0, None, None
        for k, mass in enumerate(masses):
            cdf += mass
            if lower is None and cdf >= ALPHA/2:
                lower = k
            if upper is None and cdf >= 1-ALPHA/2:
                upper = k
        assert _beta_binomial_bounds(n, a, b) == (lower, upper)
        assert math.fsum(masses[:lower]) <= ALPHA/2 + 1e-12
        assert math.fsum(masses[upper+1:]) <= ALPHA/2 + 1e-12
        if a == b == 1:
            assert all(math.isclose(m, 1/(n+1), rel_tol=1e-8) for m in masses)
            assert (lower, upper) == (1, 999)
        checks.append(dict(n=n, posterior_alpha=a, posterior_beta=b, lcl_count=lower,
                           ucl_count=upper, strict_lower_tail=math.fsum(masses[:lower]),
                           strict_upper_tail=math.fsum(masses[upper+1:])))
    # Public API: all-on-time/all-late data do not force a zero/certain risk;
    # baseline points are not evaluated against their own fitted posterior.
    for baseline_late in [0, 80]:
        baseline = [row(f"b-{i}", START + timedelta(days=i//4, hours=i%4),
                        10 if i < baseline_late else 4) for i in range(80)]
        monitored = [row(f"m-{i}", START + timedelta(days=20, seconds=i), 10) for i in range(28)]
        chart = analyze(baseline + monitored, p_method="beta_binomial")["zones"][0]["p_chart"]
        assert 0 < chart["center"] < 1
        assert all(not p["signal"] and not p["signal_evaluated"] for p in chart["points"] if p["in_baseline"])
        point = next(p for p in chart["points"] if not p["in_baseline"])
        expected = next(c for c in checks if c["n"] == 28 and c["posterior_alpha"] == baseline_late+.5)
        assert (point["lcl_count"], point["ucl_count"]) == (expected["lcl_count"], expected["ucl_count"])
    return checks


def chart_observations(zone: dict, baseline_days=BASELINE_DAYS) -> dict[str, list[tuple[int, bool]]]:
    monitoring_start = (START + timedelta(days=baseline_days)).date()
    result = {"individuals": [], "moving_range": [], "late_fraction": []}
    for point in zone["imr"]["points"]:
        if point["in_baseline"]:
            continue
        day = date.fromisoformat(point["dispatched_at"][:10])
        elapsed = (day - monitoring_start).days + 1
        result["individuals"].append((elapsed, point["signal"]))
        if point["moving_range"] is not None:
            result["moving_range"].append((elapsed, point["mr_signal"]))
    for point in zone["p_chart"]["points"]:
        if not point["in_baseline"]:
            # A batch is assessed at its END, not its first observation's date.
            elapsed = (date.fromisoformat(point["period_end"]) - monitoring_start).days + 1
            result["late_fraction"].append((elapsed, point["signal"]))
    return result


def simulation(replicates: int, p_method="beta_binomial") -> list[dict]:
    output = []
    for scenario, ratio in SCENARIOS.items():
        for scale in ["raw", "log"]:
            accumulators = {kind: dict(runs_with_signal=0, flagged=0, observed=0, first_signal_days=[])
                            for kind in ["individuals", "moving_range", "late_fraction"]}
            for replicate in range(replicates):
                rows = simulated_records(SEED + replicate, ratio)
                zone = analyze(rows, target_minutes=TARGET_MINUTES,
                               baseline_days=BASELINE_DAYS, priority="high", imr_scale=scale,
                               aggregation_days=7,p_method=p_method)["zones"][0]
                for kind, observations in chart_observations(zone).items():
                    target = accumulators[kind]
                    flagged = [day for day, signal in observations if signal]
                    target["observed"] += len(observations)
                    target["flagged"] += len(flagged)
                    if flagged:
                        target["runs_with_signal"] += 1
                        target["first_signal_days"].append(min(flagged))
            for kind, observed in accumulators.items():
                delays = observed.pop("first_signal_days")
                event_count = observed["runs_with_signal"]
                output.append(dict(scenario=scenario, monitoring_multiplier=ratio, imr_scale=scale,p_method=p_method,
                                   chart=kind, replicates=replicates, **observed,
                                   run_any_signal_proportion=event_count / replicates,
                                   run_any_signal_wilson95=wilson(event_count, replicates),
                                   flagged_observation_fraction=observed["flagged"] / observed["observed"],
                                   conditional_first_signal_day_median=median(delays) if delays else None,
                                   conditional_first_signal_day_mean=mean(delays) if delays else None))
    return output


def aggregation_comparison(replicates: int, weekly_results: list[dict],p_method="beta_binomial") -> list[dict]:
    """Show the information cost of four-call daily bins versus weekly bins."""
    output = []
    for scenario, ratio in SCENARIOS.items():
        detections, flagged_count, observation_count, delays = 0, 0, 0, []
        for replicate in range(replicates):
            zone = analyze(simulated_records(SEED + replicate, ratio), target_minutes=TARGET_MINUTES,
                           baseline_days=BASELINE_DAYS, priority="high", imr_scale="log",
                           aggregation_days=1,p_method=p_method)["zones"][0]
            points = chart_observations(zone)["late_fraction"]
            flags = [day for day, signal in points if signal]
            observation_count += len(points)
            flagged_count += len(flags)
            if flags:
                detections += 1
                delays.append(min(flags))
        output.append(dict(scenario=scenario,p_method=p_method, aggregation_days=1, replicates=replicates,
                           runs_with_signal=detections, flagged=flagged_count, observed=observation_count,
                           run_any_signal_proportion=detections / replicates,
                           run_any_signal_wilson95=wilson(detections, replicates),
                           flagged_observation_fraction=flagged_count / observation_count,
                           conditional_first_signal_day_median=median(delays) if delays else None))
        weekly = next(r for r in weekly_results if r["scenario"] == scenario and
                      r["chart"] == "late_fraction" and r["imr_scale"] == "log" and r["p_method"]==p_method)
        output.append({key: value for key, value in weekly.items()
                       if key not in ["chart", "imr_scale", "monitoring_multiplier"]} | {"aggregation_days": 7})
    return output


def demo_results() -> list[dict]:
    results = []
    for scenario in ["stable", "south_shift", "improvement"]:
        with (ROOT / "datasets" / f"{scenario}.csv").open(newline="") as handle:
            output = analyze(list(csv.DictReader(handle)), target_minutes=TARGET_MINUTES,
                             baseline_days=BASELINE_DAYS, priority="high", imr_scale="log",
                             aggregation_days=7)
        for zone in output["zones"]:
            b = zone["comparison"]["baseline"]
            m = zone["comparison"]["monitoring"]
            results.append(dict(dataset=f"{scenario}.csv", zone=zone["zone"], priority="high",
                                baseline_calls=b["count"], monitoring_calls=m["count"],
                                baseline_late_rate=b["late_rate"], monitoring_late_rate=m["late_rate"],
                                late_rate_delta_pp=zone["comparison"]["late_rate_delta_pp"],
                                baseline_p90_minutes=b["p90_minutes"], monitoring_p90_minutes=m["p90_minutes"],
                                monitoring_individual_signals=sum(p["signal"] for p in zone["imr"]["points"] if not p["in_baseline"]),
                                monitoring_mr_signals=sum(p["mr_signal"] for p in zone["imr"]["points"] if not p["in_baseline"]),
                                monitoring_late_fraction_signals=sum(p["signal"] for p in zone["p_chart"]["points"] if not p["in_baseline"])))
    return results


def robustness(replicates):
    output=[]
    for case,options in ROBUSTNESS.items():
        baseline_days=options.get('baseline_days',BASELINE_DAYS)
        for scenario in ('unchanged','slowdown_1_5x'):
            for method in METHODS:
                detections=flagged=observed=0;delays=[]
                for i in range(replicates):
                    records=simulated_records(SEED+100000+i,SCENARIOS[scenario],**options)
                    zone=analyze(records,baseline_days=baseline_days,priority='high',p_method=method)['zones'][0]
                    points=chart_observations(zone,baseline_days)['late_fraction']
                    flags=[day for day,signal in points if signal]
                    observed+=len(points);flagged+=len(flags)
                    if flags:detections+=1;delays.append(min(flags))
                output.append(dict(case=case,scenario=scenario,p_method=method,replicates=replicates,options=options,
                    runs_with_signal=detections,observed=observed,flagged=flagged,
                    run_any_signal_proportion=detections/replicates,
                    run_any_signal_wilson95=wilson(detections,replicates),
                    conditional_first_signal_day_median=median(delays) if delays else None))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=200)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results.json")
    args = parser.parse_args()
    if args.replicates < 1:
        parser.error("--replicates must be at least 1")
    known_answers = check_binomial_known_answers()
    simulation_results = [row for method in METHODS for row in simulation(args.replicates,method)]
    output = dict(
        design=dict(seed=SEED, replicates=args.replicates, baseline_days=BASELINE_DAYS,
                    monitoring_days=MONITORING_DAYS, calls_per_day=CALLS_PER_DAY,
                    zones_per_run=1, priority="high", target_minutes=TARGET_MINUTES,
                    baseline_duration_distribution="lognormal(log(7.3), 0.35)",
                    monitoring_multipliers=SCENARIOS,methods=METHODS,prior_alpha=.5,prior_beta=.5,robustness=ROBUSTNESS,robustness_replicates=min(100,args.replicates), p_chart_aggregation_days=7,
                    signal_tail_budget_known_parameter_only=ALPHA,
                    delay_definition="1-based monitoring day; p-chart signal at batch end; final partial batch included",
                    duration_resolution_seconds=1,
                    source_stats_sha256=hashlib.sha256((ROOT / "backend" / "responsewatch" / "stats.py").read_bytes()).hexdigest()),
        independent_binomial_checks=known_answers,
        independent_predictive_checks=check_predictive_known_answers(),
        robustness=robustness(min(100,args.replicates)),
        simulation=simulation_results,
        p_chart_aggregation_comparison=[row for method in METHODS for row in aggregation_comparison(args.replicates, simulation_results,method)],
        planted_demonstrations=demo_results(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(f"Saved {len(output['simulation'])} simulation summaries and {len(output['planted_demonstrations'])} demo-zone summaries to {args.output}")
    print("scenario             scale chart          runs with signals   flagged/observed   median first day (detected runs)")
    for result in output["simulation"]:
        print(f"{result['p_method']:<15} {result['scenario']:<20} {result['imr_scale']:<5} {result['chart']:<14} "
              f"{result['runs_with_signal']:>3}/{args.replicates:<4} "
              f"{result['flagged']:>5}/{result['observed']:<7} "
              f"{result['conditional_first_signal_day_median']}")


if __name__ == "__main__":
    main()
