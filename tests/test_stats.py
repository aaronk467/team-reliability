import math
import pytest
from responsewatch import analyze

def records(values, days=None):
    return [dict(id=str(i),zone='A',priority='high',dispatched_at=f'2026-01-{(days[i] if days else 1):02d}T00:00:00Z',arrived_at=f'2026-01-{(days[i] if days else 1):02d}T00:{v:02d}:00Z') for i,v in enumerate(values)]

def test_known_imr_and_summary():
    out=analyze(records([4,6,8,10,30],[1,1,1,1,2]),baseline_days=1)
    zone=out['zones'][0]; chart=zone['imr']
    assert chart['center']==7
    assert chart['mr_center']==2
    assert chart['ucl']==pytest.approx(7+6/1.128)
    assert chart['mr_ucl']==pytest.approx(6.534)
    assert chart['points'][-1]['signal']
    assert chart['points'][-1]['mr_signal']
    assert out['summary']['late_rate']==.4
    assert out['summary']['p90_minutes']==pytest.approx(22)

def test_known_p_limits_and_wilson():
    zone=analyze(records([4,10,4,10,10,10],[1,1,1,1,2,2]),baseline_days=1)['zones'][0]
    assert zone['p_chart']['center']==.5
    assert zone['p_chart']['points'][1]['ucl']==1
    # 3/6? Four late out of six; compare published Wilson computation separately.
    assert zone['late_rate']==pytest.approx(4/6)
    assert zone['late_ci_low']==pytest.approx(.2999933151)
    assert zone['late_ci_high']==pytest.approx(.9032285889)

def test_frozen_limits_and_constant():
    a=analyze(records([4,6,8],[1,1,2]),baseline_days=1)
    b=analyze(records([4,6,50],[1,1,2]),baseline_days=1)
    assert a['zones'][0]['imr']['ucl']==b['zones'][0]['imr']['ucl']
    assert analyze(records([4,4]))['zones'][0]['imr']['ucl'] is None

@pytest.mark.parametrize('mutate',[lambda r:r[0].update(arrived_at='2025-01-01T00:00:00Z'),lambda r:r[0].update(dispatched_at='2026-01-01T00:00:00'),lambda r:r[1].update(id='0')])
def test_invalid_records(mutate):
    rows=records([4,6]); mutate(rows)
    with pytest.raises(ValueError): analyze(rows)

def test_target_boundary_and_priority():
    rows=records([8,9]); rows[1]['priority']='low'
    assert analyze(rows,priority='high')['summary']['late_count']==0
    with pytest.raises(ValueError): analyze(rows,target_minutes=float('nan'))

def test_variable_denominator_p_chart_known_limits():
    rows=[]
    for day,n in [(1,100),(2,25)]:
        for i in range(n):
            row=records([4 if i%2==0 else 10],[day])[0]
            row['id']=f'{day}-{i}'
            rows.append(row)
    chart=analyze(rows,baseline_days=1)['zones'][0]['p_chart']
    assert chart['center']==.5
    assert chart['points'][0]['lcl']==pytest.approx(.35)
    assert chart['points'][0]['ucl']==pytest.approx(.65)
    assert chart['points'][1]['lcl']==pytest.approx(.2)
    assert chart['points'][1]['ucl']==pytest.approx(.8)

def test_sparse_zones_and_degenerate_proportions():
    rows=records([4,10],[1,2]); rows[1]['zone']='B'
    out=analyze(rows,baseline_days=1)
    a,b=out['zones']
    assert a['imr']['ucl'] is None
    assert a['p_chart']['center']==0
    assert b['baseline_count']==0
    assert b['p_chart']['points'][0]['ucl'] is None
    assert not b['p_chart']['points'][0]['signal']
    assert analyze(records([10]))['zones'][0]['p_chart']['center']==1

def test_planted_south_shift_in_demo():
    import csv
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]/'datasets'
    with (root/'south_shift.csv').open() as file:
        output=analyze(list(csv.DictReader(file)))
    south=next(z for z in output['zones'] if z['zone']=='South')
    assert any(p['signal'] and not p['in_baseline'] and p['dispatched_at'][:10]>'2026-01-20' for p in south['imr']['points'])

def test_baseline_instability_warning_reports_signals():
    # A single isolated 40-minute dispatch among alternating 4/6-minute calls
    # lies beyond its own estimated baseline limits; warn before using them.
    values=[4,6]*15+[40]+[4,6]*15
    rows=[]
    for i,value in enumerate(values):
        row=records([value])[0]
        row['id']=str(i)
        rows.append(row)
    zone=analyze(rows,baseline_days=1)['zones'][0]
    assert sum(p['signal'] for p in zone['imr']['points'])==1
    assert sum(p['mr_signal'] for p in zone['imr']['points'])==2
    warning=next(w for w in zone['warnings'] if 'Baseline may be unstable' in w)
    assert '1 I-chart, 2 moving-range, and 0 p-chart' in warning
