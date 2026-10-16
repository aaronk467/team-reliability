import pytest
from responsewatch.stats import validate_records
from responsewatch.delay_patterns import summarize_delays


def rows():
    return validate_records([
        dict(id='1',zone='A',priority='high',dispatched_at='2026-01-01T12:00:00Z',arrived_at='2026-01-01T12:10:00Z',delay_reason=' Traffic ',shift='day',traffic='heavy',units_available='0'),
        dict(id='2',zone='A',priority='high',dispatched_at='2026-01-01T13:00:00Z',arrived_at='2026-01-01T13:11:00Z',delay_reason='',shift='day',units_available=4),
        dict(id='3',zone='A',priority='high',dispatched_at='2026-01-01T22:00:00Z',arrived_at='2026-01-01T22:05:00Z',delay_reason='unknown',shift='night',traffic='light'),
    ])


def test_missing_reasons_are_not_dropped_from_pareto_or_group_denominators():
    result=summarize_delays(rows(),8)
    assert result['reason_coverage']==pytest.approx(1/3)
    assert result['late_reason_coverage']==.5
    assert sum(r['late_count'] for r in result['reasons'])==2
    assert result['reasons'][-1]['cumulative_late_share']==1
    assert {r['reason']:r['late_share'] for r in result['reasons']}=={'Not recorded':.5,'traffic':.5}
    assert all(sum(g['count'] for g in s['groups'])==3 for s in result['strata'])
    units=next(s for s in result['strata'] if s['field']=='units_available')
    assert units['missing_count']==1
    assert {g['value'] for g in units['groups']}=={'0','3+','Not recorded'}


@pytest.mark.parametrize('bad',[True,-1,1.5,'3.5','-1'])
def test_invalid_unit_context_is_rejected(bad):
    data=rows();data[0]['units_available']=bad
    with pytest.raises(ValueError,match='units_available'):
        summarize_delays(data,8)


def test_no_late_calls_have_no_invented_late_reason_fraction():
    result=summarize_delays(rows(),100)
    assert result['late_reason_coverage'] is None
    assert all(r['late_share'] is None and r['cumulative_late_share'] is None for r in result['reasons'])
