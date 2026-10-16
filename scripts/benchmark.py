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
MONITORING_START = (START + timedelta(days=BASELINE_DAYS)).date()
ALPHA = math.erfc(3 / math.sqrt(2))
SCENARIOS = {"unchanged": 1.0, "slowdown_1_5x": 1.5, "improvement_0_72x": 0.72}


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


def simulated_records(seed: int, ratio: float) -> list[dict]:
    """Independent lognormal durations; common random draws across scenarios."""
    rng = random.Random(seed)
    rows = []
    for day in range(BASELINE_DAYS + MONITORING_DAYS):
        for call in range(CALLS_PER_DAY):
            minutes = rng.lognormvariate(math.log(7.3), 0.35)
            if day >= BASELINE_DAYS:
                minutes *= ratio
            rows.append(row(f"{day}-{call}", START + timedelta(days=day, hours=6 * call), minutes))
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
                             baseline_days=BASELINE_DAYS, priority="high", aggregation_days=7)
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


def chart_observations(zone: dict) -> dict[str, list[tuple[int, bool]]]:
    result = {"individuals": [], "moving_range": [], "late_fraction": []}
    for point in zone["imr"]["points"]:
        if point["in_baseline"]:
            continue
        day = date.fromisoformat(point["dispatched_at"][:10])
        elapsed = (day - MONITORING_START).days + 1
        result["individuals"].append((elapsed, point["signal"]))
        if point["moving_range"] is not None:
            result["moving_range"].append((elapsed, point["mr_signal"]))
    for point in zone["p_chart"]["points"]:
        if not point["in_baseline"]:
            # A batch is assessed at its END, not its first observation's date.
            elapsed = (date.fromisoformat(point["period_end"]) - MONITORING_START).days + 1
            result["late_fraction"].append((elapsed, point["signal"]))
    return result


def simulation(replicates: int) -> list[dict]:
    output = []
    for scenario, ratio in SCENARIOS.items():
        for scale in ["raw", "log"]:
            accumulators = {kind: dict(runs_with_signal=0, flagged=0, observed=0, first_signal_days=[])
                            for kind in ["individuals", "moving_range", "late_fraction"]}
            for replicate in range(replicates):
                rows = simulated_records(SEED + replicate, ratio)
                zone = analyze(rows, target_minutes=TARGET_MINUTES,
                               baseline_days=BASELINE_DAYS, priority="high", imr_scale=scale,
                               aggregation_days=7)["zones"][0]
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
                output.append(dict(scenario=scenario, monitoring_multiplier=ratio, imr_scale=scale,
                                   chart=kind, replicates=replicates, **observed,
                                   run_any_signal_proportion=event_count / replicates,
                                   run_any_signal_wilson95=wilson(event_count, replicates),
                                   flagged_observation_fraction=observed["flagged"] / observed["observed"],
                                   conditional_first_signal_day_median=median(delays) if delays else None,
                                   conditional_first_signal_day_mean=mean(delays) if delays else None))
    return output


def aggregation_comparison(replicates: int, weekly_results: list[dict]) -> list[dict]:
    """Show the information cost of four-call daily bins versus weekly bins."""
    output = []
    for scenario, ratio in SCENARIOS.items():
        detections, flagged_count, observation_count, delays = 0, 0, 0, []
        for replicate in range(replicates):
            zone = analyze(simulated_records(SEED + replicate, ratio), target_minutes=TARGET_MINUTES,
                           baseline_days=BASELINE_DAYS, priority="high", imr_scale="log",
                           aggregation_days=1)["zones"][0]
            points = chart_observations(zone)["late_fraction"]
            flags = [day for day, signal in points if signal]
            observation_count += len(points)
            flagged_count += len(flags)
            if flags:
                detections += 1
                delays.append(min(flags))
        output.append(dict(scenario=scenario, aggregation_days=1, replicates=replicates,
                           runs_with_signal=detections, flagged=flagged_count, observed=observation_count,
                           run_any_signal_proportion=detections / replicates,
                           run_any_signal_wilson95=wilson(detections, replicates),
                           flagged_observation_fraction=flagged_count / observation_count,
                           conditional_first_signal_day_median=median(delays) if delays else None))
        weekly = next(r for r in weekly_results if r["scenario"] == scenario and
                      r["chart"] == "late_fraction" and r["imr_scale"] == "log")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=200)
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results.json")
    args = parser.parse_args()
    if args.replicates < 1:
        parser.error("--replicates must be at least 1")
    known_answers = check_binomial_known_answers()
    simulation_results = simulation(args.replicates)
    output = dict(
        design=dict(seed=SEED, replicates=args.replicates, baseline_days=BASELINE_DAYS,
                    monitoring_days=MONITORING_DAYS, calls_per_day=CALLS_PER_DAY,
                    zones_per_run=1, priority="high", target_minutes=TARGET_MINUTES,
                    baseline_duration_distribution="lognormal(log(7.3), 0.35)",
                    monitoring_multipliers=SCENARIOS, p_chart_aggregation_days=7,
                    signal_tail_budget_known_parameter_only=ALPHA,
                    delay_definition="1-based monitoring day; p-chart signal at batch end; final partial batch included",
                    duration_resolution_seconds=1,
                    source_stats_sha256=hashlib.sha256((ROOT / "backend" / "responsewatch" / "stats.py").read_bytes()).hexdigest()),
        independent_binomial_checks=known_answers,
        simulation=simulation_results,
        p_chart_aggregation_comparison=aggregation_comparison(args.replicates, simulation_results),
        planted_demonstrations=demo_results(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(f"Saved {len(output['simulation'])} simulation summaries and {len(output['planted_demonstrations'])} demo-zone summaries to {args.output}")
    print("scenario             scale chart          runs with signals   flagged/observed   median first day (detected runs)")
    for result in output["simulation"]:
        print(f"{result['scenario']:<20} {result['imr_scale']:<5} {result['chart']:<14} "
              f"{result['runs_with_signal']:>3}/{args.replicates:<4} "
              f"{result['flagged']:>5}/{result['observed']:<7} "
              f"{result['conditional_first_signal_day_median']}")


if __name__ == "__main__":
    main()
