"""Reproduce fictional, seeded dispatch-to-arrival demonstrations (stdlib only)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import random

ROOT = Path(__file__).resolve().parent
FIELDS = ['id', 'zone', 'priority', 'dispatched_at', 'arrived_at', 'delay_reason']

def generate(scenario: str, seed: int = 467) -> None:
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for day in range(45):
        for zone in ['North', 'Central', 'South', 'East']:
            for call in range(8):
                priority = 'high' if call < 4 else 'standard'
                # Same random stream across scenarios makes comparisons transparent.
                dispatched = start + timedelta(days=day, seconds=rng.randrange(86400))
                median = 7.3 if priority == 'high' else 11.2
                zone_effect = {'North': 0.0, 'Central': -0.4, 'South': 0.3, 'East': 0.5}[zone]
                minutes = rng.lognormvariate(0, 0.22) * (median + zone_effect)
                rare_delay = rng.random() < 0.035
                reason = ''
                if rare_delay:
                    minutes += rng.uniform(7, 14)
                    reason = rng.choice(['traffic', 'unit_unavailable', 'access_delay'])
                if day >= 20 and scenario == 'south_shift' and zone == 'South':
                    minutes += 5.0
                    reason = 'unit_unavailable'
                if day >= 20 and scenario == 'improvement':
                    minutes *= 0.72
                arrived = dispatched + timedelta(seconds=round(minutes * 60))
                rows.append({
                    'id': f'{scenario}-{day + 1:02d}-{zone[0]}-{call + 1:02d}',
                    'zone': zone, 'priority': priority,
                    'dispatched_at': dispatched.isoformat().replace('+00:00', 'Z'),
                    'arrived_at': arrived.isoformat().replace('+00:00', 'Z'),
                    'delay_reason': reason,
                })
    rows.sort(key=lambda row: row['dispatched_at'])
    with (ROOT / f'{scenario}.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

if __name__ == '__main__':
    for name in ['stable', 'south_shift', 'improvement']:
        generate(name)
