"""Check the shipped demonstrations independently of their generating formulas."""
from collections import Counter
import csv
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / 'datasets'
SCENARIOS = ('stable', 'south_shift', 'improvement')
CUTOFF = datetime(2026, 1, 21, tzinfo=timezone.utc)


def read_rows(scenario):
    with (DATASETS / f'{scenario}.csv').open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def duration_seconds(row):
    return (datetime.fromisoformat(row['arrived_at']) - datetime.fromisoformat(row['dispatched_at'])).total_seconds()


def test_generator_reproduces_exactly_three_bundled_csvs_without_editing_them(tmp_path):
    originals = {name: (DATASETS / f'{name}.csv').read_bytes() for name in SCENARIOS}
    subprocess.run(
        [sys.executable, str(DATASETS / 'generate.py'), '--output-dir', str(tmp_path)],
        check=True,
    )
    assert {path.name for path in tmp_path.iterdir()} == {f'{name}.csv' for name in SCENARIOS}
    assert {path.name for path in DATASETS.glob('*.csv')} == {f'{name}.csv' for name in SCENARIOS}
    for name in SCENARIOS:
        output = (tmp_path / f'{name}.csv').read_bytes()
        assert output == originals[name]
        assert (DATASETS / f'{name}.csv').read_bytes() == originals[name]
        assert b'\r' not in output


@pytest.mark.parametrize('scenario', SCENARIOS)
def test_demonstration_records_have_valid_completed_calls_and_dispatch_context(scenario):
    rows = read_rows(scenario)
    assert len(rows) == 1781
    assert len({row['id'] for row in rows}) == len(rows)
    assert {'id', 'zone', 'priority', 'dispatched_at', 'arrived_at'} <= rows[0].keys()
    assert {row['zone'] for row in rows} == {'North', 'Central', 'South', 'East'}
    assert {row['priority'] for row in rows} == {'high', 'standard'}
    assert {row['traffic'] for row in rows} == {'light', 'moderate', 'heavy'}
    assert {int(row['units_available']) for row in rows} == set(range(5))
    assert {row['delay_reason'] for row in rows} <= {'', 'traffic', 'unit_unavailable', 'access_delay'}
    for row in rows:
        dispatch = datetime.fromisoformat(row['dispatched_at'])
        arrival = datetime.fromisoformat(row['arrived_at'])
        assert dispatch.utcoffset().total_seconds() == 0
        assert arrival.utcoffset().total_seconds() == 0
        assert arrival > dispatch
        assert row['shift'] == ('day' if 7 <= dispatch.hour < 19 else 'night')
    assert [row['dispatched_at'] for row in rows] == sorted(row['dispatched_at'] for row in rows)


def test_field_like_demand_and_incomplete_annotations_are_present():
    rows = read_rows('stable')
    dates = {row['dispatched_at'][:10] for row in rows}
    assert len(dates) == 45
    assert min(dates) == '2026-01-01'
    assert max(dates) == '2026-02-14'
    daily = Counter((row['zone'], row['dispatched_at'][:10]) for row in rows)
    high_daily = Counter((row['zone'], row['dispatched_at'][:10]) for row in rows if row['priority'] == 'high')
    assert len(set(daily.values())) >= 8  # Demand is visibly nonuniform.
    assert len(set(high_daily.values())) >= 5
    assert sum(row['shift'] == 'day' for row in rows) > sum(row['shift'] == 'night' for row in rows)
    annotated = sum(bool(row['delay_reason']) for row in rows)
    assert 0 < annotated < len(rows)
    baseline_high = Counter(
        row['zone'] for row in rows
        if row['priority'] == 'high' and datetime.fromisoformat(row['dispatched_at']) < CUTOFF
    )
    assert all(baseline_high[zone] >= 60 for zone in ('North', 'Central', 'South', 'East'))


def test_scenarios_keep_paired_calls_and_only_the_documented_duration_changes():
    by_scenario = {
        name: {row['id'].removeprefix(f'{name}-'): row for row in read_rows(name)}
        for name in SCENARIOS
    }
    reference = by_scenario['stable']
    for scenario in ('south_shift', 'improvement'):
        assert by_scenario[scenario].keys() == reference.keys()
        for identifier, base in reference.items():
            other = by_scenario[scenario][identifier]
            for field in ('zone', 'priority', 'dispatched_at', 'shift', 'traffic', 'units_available'):
                assert other[field] == base[field]
            before_change = datetime.fromisoformat(base['dispatched_at']) < CUTOFF
            base_seconds = duration_seconds(base)
            actual_seconds = duration_seconds(other)
            if before_change:
                assert actual_seconds == base_seconds
                assert other['delay_reason'] == base['delay_reason']
            elif scenario == 'south_shift':
                assert actual_seconds == base_seconds + (300 if base['zone'] == 'South' else 0)
                if base['zone'] == 'South':
                    assert other['delay_reason'] == 'unit_unavailable'
            else:
                # Each scenario rounds its latent duration to one second.
                assert abs(actual_seconds - 0.72 * base_seconds) <= 1
                assert other['delay_reason'] == base['delay_reason']
