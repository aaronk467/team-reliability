"""Reproduce fictional, paired dispatch logs using Python's standard library.

Run ``python datasets/generate.py --output-dir /tmp/responsewatch-data`` to
verify reproducibility without touching the bundled files. The scenarios share
the same draws, so their planted outcome changes can be checked call by call.
The demand and context assumptions are illustrative, not fitted field data.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS = ('stable', 'south_shift', 'improvement')
FIELDS = [
    'id', 'zone', 'priority', 'dispatched_at', 'arrived_at', 'delay_reason',
    'shift', 'traffic', 'units_available',
]
ZONES = ('North', 'Central', 'South', 'East')
DAILY_DEMAND = {'North': 9.0, 'Central': 12.0, 'South': 10.0, 'East': 8.0}
ZONE_EFFECT = {'North': 0.0, 'Central': -0.4, 'South': 0.3, 'East': 0.5}


def _poisson(rng: random.Random, mean: float) -> int:
    """Knuth sampler; daily means are small enough for this exact algorithm."""
    threshold = math.exp(-mean)
    product = 1.0
    count = 0
    while product > threshold:
        count += 1
        product *= rng.random()
    return count - 1


def scenario_rows(scenario: str, seed: int = 467) -> list[dict[str, str]]:
    """Return 45 days of paired completed calls with known scenario changes.

    Demand varies across zones and weekends. Pre-dispatch context has modest
    effects on duration; reason labels are incomplete descriptive annotations.
    Arrivals are rounded to whole seconds, matching the CSV timestamp precision.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f'Unknown scenario: {scenario}')
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for day in range(45):
        date = start + timedelta(days=day)
        weekend = date.weekday() >= 5
        for zone in ZONES:
            count = _poisson(rng, DAILY_DEMAND[zone] * (0.85 if weekend else 1.08))
            for call in range(count):
                # More dispatches during waking hours, with some overnight calls.
                daytime = rng.random() < (0.62 if weekend else 0.70)
                hour = rng.randrange(7, 19) if daytime else rng.choice((*range(7), *range(19, 24)))
                dispatched = date + timedelta(hours=hour, seconds=rng.randrange(3600))
                shift = 'day' if daytime else 'night'
                rush_hour = not weekend and (7 <= hour < 10 or 16 <= hour < 19)
                traffic_weights = (5, 30, 65) if rush_hour else ((20, 60, 20) if daytime else (65, 30, 5))
                traffic = rng.choices(('light', 'moderate', 'heavy'), weights=traffic_weights, k=1)[0]
                units = rng.choices(range(5), weights=(8, 24, 36, 24, 8) if daytime else (5, 15, 35, 30, 15), k=1)[0]
                priority = 'high' if rng.random() < (0.50 if daytime else 0.44) else 'standard'
                median = (7.3 if priority == 'high' else 11.2) + ZONE_EFFECT[zone]
                traffic_factor = {'light': 0.90, 'moderate': 1.0, 'heavy': 1.17}[traffic]
                unit_factor = 1.18 if units == 0 else (1.08 if units == 1 else 1.0)
                minutes = rng.lognormvariate(0, 0.22) * median * traffic_factor * unit_factor * (1.0 if daytime else 0.95)
                rare_delay = rng.random() < 0.035
                reason = ''
                if rare_delay:
                    minutes += rng.uniform(7, 14)
                    reason = rng.choice(('traffic', 'unit_unavailable', 'access_delay'))
                # Recording is incomplete: blank does not mean absence of delay.
                elif units == 0 and rng.random() < 0.75:
                    reason = 'unit_unavailable'
                elif traffic == 'heavy' and rng.random() < 0.70:
                    reason = 'traffic'
                elif rng.random() < 0.10:
                    reason = 'access_delay'
                if day >= 20 and scenario == 'south_shift' and zone == 'South':
                    minutes += 5.0
                    reason = 'unit_unavailable'
                if day >= 20 and scenario == 'improvement':
                    minutes *= 0.72
                arrived = dispatched + timedelta(seconds=round(minutes * 60))
                rows.append({
                    'id': f'{scenario}-{day + 1:02d}-{zone[0]}-{call + 1:02d}',
                    'zone': zone,
                    'priority': priority,
                    'dispatched_at': dispatched.isoformat().replace('+00:00', 'Z'),
                    'arrived_at': arrived.isoformat().replace('+00:00', 'Z'),
                    'delay_reason': reason,
                    'shift': shift,
                    'traffic': traffic,
                    'units_available': str(units),
                })
    rows.sort(key=lambda row: (row['dispatched_at'], row['id']))
    return rows


def generate(scenario: str, seed: int = 467, output_dir: Path = ROOT) -> Path:
    """Write a deterministic UTF-8/LF scenario CSV and return its path."""
    rows = scenario_rows(scenario, seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f'{scenario}.csv'
    with destination.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT, help='Directory for the three CSV files.')
    parser.add_argument('--seed', type=int, default=467, help='Random seed (bundled demonstrations use 467).')
    args = parser.parse_args()
    for name in SCENARIOS:
        generate(name, seed=args.seed, output_dir=args.output_dir)
