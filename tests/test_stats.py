import math
import pytest
from responsewatch import analyze

def records(values, days=None):
    return [dict(id=str(i),zone='A',priority='high',dispatched_at=f'2026-01-{(days[i] if days else 1):02d}T00:00:00Z',arrived_at=f'2026-01-{(days[i] if days else 1):02d}T00:{v:02d}:00Z') for i,v in enumerate(values)]

def test_known_imr_and_summary():
    out=analyze(records([4,6,8,10,30],[1,1,1,1,2]),baseline_days=1,imr_scale='raw')
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
    zone=analyze(records([4,10,4,10,10,10],[1,1,1,1,2,2]),baseline_days=1,aggregation_days=1)['zones'][0]
    assert zone['p_chart']['center']==.5
    assert zone['p_chart']['points'][1]['ucl']==1
    # Four late out of six; independently known Wilson score endpoints.
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
    chart=analyze(rows,baseline_days=1,aggregation_days=1,p_method='exact_binomial')['zones'][0]['p_chart']
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
    assert a['p_chart']['baseline_late_rate']==0
    assert a['p_chart']['center']==.25
    assert b['baseline_count']==0
    assert b['p_chart']['points'][0]['ucl'] is None
    assert not b['p_chart']['points'][0]['signal']
    assert analyze(records([10]))['zones'][0]['p_chart']['baseline_late_rate']==1
    assert analyze(records([10]))['zones'][0]['p_chart']['center']==.75

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
    zone=analyze(rows,baseline_days=1,imr_scale='raw')['zones'][0]
    assert sum(p['signal'] for p in zone['imr']['points'])==1
    assert sum(p['mr_signal'] for p in zone['imr']['points'])==2
    warning=next(w for w in zone['warnings'] if 'Baseline may be unstable' in w)
    assert '1 I-chart and 2 moving-range' in warning
    assert 'predictive p points are not evaluated' in warning

def precise_records(values, days=None):
    from datetime import datetime,timedelta,timezone
    result=[]
    for i,value in enumerate(values):
        dispatched=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=(days[i]-1 if days else 0),seconds=i)
        result.append(dict(id=str(i),zone='A',priority='high',dispatched_at=dispatched.isoformat(),arrived_at=(dispatched+timedelta(minutes=value)).isoformat()))
    return result


def test_log_chart_known_transformation_and_units():
    # log(x)=[0,1,2], mean=1, mean moving range=1.
    zone=analyze(precise_records([1,math.e,math.e**2]))['zones'][0]
    chart=zone['imr']
    assert chart['scale']=='log'
    assert chart['mr_units']=='log ratio'
    assert chart['center']==pytest.approx(math.e)
    assert chart['mr_center']==pytest.approx(1)
    assert chart['mr_ucl']==pytest.approx(3.267)
    assert chart['lcl']==pytest.approx(math.exp(1-3/1.128))
    assert chart['ucl']==pytest.approx(math.exp(1+3/1.128))
    assert chart['points'][1]['moving_range']==pytest.approx(1)


def test_binomial_bounds_match_independent_exact_enumeration():
    from responsewatch.stats import _binomial_bounds,CHART_ALPHA
    # Independent comb-based PMF is safe at these modest n. Production uses
    # mode recurrences to stay stable for much larger and more extreme n,p.
    for n,p in [(4,.25),(25,.5),(100,.5),(80,.125)]:
        pmf=[math.comb(n,k)*p**k*(1-p)**(n-k) for k in range(n+1)]
        def quantile(q):
            return next(k for k in range(n+1) if math.fsum(pmf[:k+1])>=q)
        low,high=_binomial_bounds(n,p)
        assert (low,high)==(quantile(CHART_ALPHA/2),quantile(1-CHART_ALPHA/2))
        assert math.fsum(pmf[:low]) <= CHART_ALPHA/2
        assert math.fsum(pmf[high+1:]) <= CHART_ALPHA/2
    assert _binomial_bounds(100000,.5)==(49526,50474)
    assert _binomial_bounds(1000,.001)==(0,5)


def test_bins_reset_at_baseline_boundary_and_use_actual_denominators():
    # 3-day baseline must not bleed into the 7-day monitoring bin.
    rows=precise_records([4,10,4,10,4],[1,3,4,6,12])
    out=analyze(rows,baseline_days=3,aggregation_days=7)
    points=out['zones'][0]['p_chart']['points']
    assert [(p['period_start'],p['period_end'],p['n'],p['in_baseline']) for p in points]==[
        ('2026-01-01','2026-01-03',2,True),
        ('2026-01-04','2026-01-10',2,False),
        ('2026-01-11','2026-01-12',1,False)]
    changed=analyze(precise_records([4,10,50,50,50],[1,3,4,6,12]),baseline_days=3,aggregation_days=7)
    a,b=out['zones'][0],changed['zones'][0]
    assert a['imr']['ucl']==b['imr']['ucl']
    assert a['p_chart']['center']==b['p_chart']['center']
    assert [(p['lcl'],p['ucl']) for p in a['p_chart']['points']]==[(p['lcl'],p['ucl']) for p in b['p_chart']['points']]


def test_before_after_observed_effects_and_missing_periods():
    out=analyze(precise_records([4,10,10,12],[1,1,2,2]),baseline_days=1)
    before_after=out['comparison']
    assert before_after==out['zones'][0]['comparison']
    assert before_after['baseline']['count']==2
    assert before_after['monitoring']['count']==2
    assert before_after['late_rate_delta_pp']==50
    assert before_after['p90_delta_minutes']==pytest.approx(2.4)
    baseline_only=analyze(precise_records([4,10]))['comparison']
    assert baseline_only['monitoring'] is None
    assert baseline_only['late_rate_delta_pp'] is None
    rows=precise_records([4,10],[1,2]);rows[1]['zone']='B'
    b=analyze(rows,baseline_days=1)['zones'][1]['comparison']
    assert b['baseline'] is None
    assert b['monitoring']['count']==1
    assert b['p90_delta_minutes'] is None


def test_zero_log_behavior_never_uses_invented_offset():
    baseline_zero=analyze(precise_records([0,4,10]))['zones'][0]
    assert baseline_zero['imr']['center'] is None
    assert baseline_zero['imr']['ucl'] is None
    assert any('Zero-minute' in w for w in baseline_zero['warnings'])
    monitored=analyze(precise_records([4,6,0,10],[1,1,2,2]),baseline_days=1)['zones'][0]
    assert monitored['imr']['ucl'] is not None
    assert monitored['imr']['points'][2]['moving_range'] is None
    assert monitored['imr']['points'][3]['moving_range'] is None
    assert not monitored['imr']['points'][2]['signal']
    raw=analyze(precise_records([0,4,10]),imr_scale='raw')['zones'][0]
    assert raw['imr']['ucl'] is not None
    assert raw['imr']['mr_units']=='minutes'


@pytest.mark.parametrize('kwargs',[{'aggregation_days':True},{'aggregation_days':0},{'aggregation_days':366},{'imr_scale':'invalid'}])
def test_invalid_new_settings(kwargs):
    with pytest.raises(ValueError):analyze(records([4,6]),**kwargs)


def test_beta_binomial_uniform_known_answer():
    from responsewatch.stats import _beta_binomial_bounds,CHART_ALPHA
    # Beta(1,1) mixing yields P(K=k)=1/(n+1), so inverse CDF is analytic.
    for n in (4, 19, 1000):
        expected_low=math.ceil(CHART_ALPHA/2*(n+1))-1
        expected_high=math.ceil((1-CHART_ALPHA/2)*(n+1))-1
        assert _beta_binomial_bounds(n,1,1)==(expected_low,expected_high)
    assert _beta_binomial_bounds(1000,1,1)==(1,999)


def test_beta_binomial_bounds_match_independent_beta_function_enumeration():
    from responsewatch.stats import _beta_binomial_bounds,CHART_ALPHA
    # Independent combinatorial/Beta-function evaluation, not production's
    # adjacent-mass recurrence. Includes endpoint modes and a U-shaped case.
    for n,a,b in [(4,.5,4.5),(28,10.5,70.5),(100,33.5,47.5),(28,80.5,.5),(40,.5,.5),(19,1,3)]:
        def beta_log(x,y):
            return math.lgamma(x)+math.lgamma(y)-math.lgamma(x+y)
        pmf=[math.comb(n,k)*math.exp(beta_log(k+a,n-k+b)-beta_log(a,b)) for k in range(n+1)]
        assert math.fsum(pmf)==pytest.approx(1,abs=1e-12)
        def quantile(q):
            return next(k for k in range(n+1) if math.fsum(pmf[:k+1])>=q)
        low,high=_beta_binomial_bounds(n,a,b)
        assert (low,high)==(quantile(CHART_ALPHA/2),quantile(1-CHART_ALPHA/2))
        assert math.fsum(pmf[:low]) <= CHART_ALPHA/2+1e-12
        assert math.fsum(pmf[high+1:]) <= CHART_ALPHA/2+1e-12


def test_beta_binomial_large_bins_stable_and_symmetric():
    from responsewatch.stats import _beta_binomial_bounds,_binomial_bounds
    low,high=_beta_binomial_bounds(100000,50000.5,50000.5)
    assert low+high==100000
    assert 0<low<49526<50474<high<100000  # Wider than known-p Binomial.
    rare=_beta_binomial_bounds(100000,.5,100000.5)
    common=_beta_binomial_bounds(100000,100000.5,.5)
    assert rare[0]==0 and 0<rare[1]<100000
    assert common==(100000-rare[1],100000-rare[0])


def test_predictive_posterior_is_frozen_and_baseline_is_not_a_forecast():
    rows=precise_records([4,10,10,12],[1,1,2,2])
    a=analyze(rows,baseline_days=1)['zones'][0]['p_chart']
    changed=analyze(precise_records([4,10,4,4],[1,1,2,2]),baseline_days=1)['zones'][0]['p_chart']
    assert a['method']=='beta_binomial'
    assert a['prior_alpha']==a['prior_beta']==.5
    assert a['posterior_alpha']==a['posterior_beta']==1.5
    assert a['posterior_mean']==a['center']==.5
    assert a['baseline_late_rate']==.5
    assert a['baseline_signal_policy']=='not_evaluated_fitted_reference'
    assert not a['points'][0]['signal_evaluated'] and not a['points'][0]['signal']
    assert a['points'][1]['signal_evaluated']
    for key in ('posterior_alpha','posterior_beta','posterior_mean','center'):
        assert a[key]==changed[key]
    assert [(p['lcl_count'],p['ucl_count']) for p in a['points']]==[(p['lcl_count'],p['ucl_count']) for p in changed['points']]


def test_zero_or_all_late_baseline_has_predictive_uncertainty():
    for baseline_value in (4,10):
        baseline_values=[baseline_value]*4
        rows=precise_records(baseline_values+[4]*28,[1]*4+[2]*28)
        output=analyze(rows,baseline_days=1)
        chart=output['zones'][0]['p_chart']
        assert 0<chart['posterior_mean']<1
        period=chart['points'][1]
        assert period['lcl_count']<period['ucl_count']
        legacy=analyze(rows,baseline_days=1,p_method='exact_binomial')['zones'][0]['p_chart']
        assert legacy['posterior_alpha'] is None
        assert legacy['prior_alpha'] is None
        assert legacy['center'] in (0,1)
        assert legacy['points'][1]['lcl_count']==legacy['points'][1]['ucl_count']


def test_baseline_quality_marks_instability_and_short_or_missing_reference():
    values=[4,6]*15+[40]+[4,6]*15
    unstable=analyze(precise_records(values),imr_scale='raw')['zones'][0]['baseline_quality']
    assert unstable['review_recommended']
    assert unstable['i_signals']==1 and unstable['mr_signals']==2
    assert unstable['p_signals'] is None
    assert unstable['imr_limits_available']
    assert any('I/MR signals' in reason for reason in unstable['reasons'])
    rows=precise_records([4,10],[1,2]);rows[1]['zone']='B'
    absent=analyze(rows,baseline_days=1)['zones'][1]
    assert absent['baseline_quality']['review_recommended']
    assert not absent['baseline_quality']['imr_limits_available']
    assert absent['p_chart']['posterior_mean'] is None
    assert not absent['p_chart']['points'][0]['signal_evaluated']


@pytest.mark.parametrize('method',['bad','',None,1,[],{}])
def test_invalid_p_method(method):
    with pytest.raises(ValueError):analyze(records([4,6]),p_method=method)
