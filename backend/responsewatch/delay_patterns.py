"""Descriptive delay context. Associations and recorded reasons are not causes."""
from collections import defaultdict
import re
from .stats import _summary

MISSING = 'Not recorded'
UNKNOWN = {'', 'unknown', 'unspecified', 'not recorded', 'n/a'}


def _text(value, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f'{field} must be a string or null')
    value = value.strip().casefold()
    return None if value in UNKNOWN else value


def _unit_band(value):
    if value is None or isinstance(value, str) and value.strip().casefold() in UNKNOWN:
        return None
    if isinstance(value, bool):
        raise ValueError('units_available must be a nonnegative integer or blank')
    if isinstance(value, str) and re.fullmatch(r'[0-9]+', value.strip()):
        value = int(value.strip())
    if not isinstance(value, int) or value < 0:
        raise ValueError('units_available must be a nonnegative integer or blank')
    return str(value) if value < 3 else '3+'


def validate_context(row):
    """Validate optional pre-dispatch context without inventing missing values."""
    _text(row.get("shift"), "shift")
    _text(row.get("traffic"), "traffic")
    _unit_band(row.get("units_available"))


def summarize_delays(rows, target):
    """Summarize normalized completed calls, with missing context in denominators.

    Reason Pareto shares use ALL late calls, including unrecorded reasons.
    Context groups are unadjusted all-period summaries, not risk-adjusted or
    baseline/monitoring effect estimates. Optional context is never inferred.
    """
    reasons = defaultdict(list)
    contexts = {field: defaultdict(list) for field in ('shift', 'traffic', 'units_available')}
    reason_count = late_reason_count = 0
    for row in rows:
        reason = _text(row.get('delay_reason'), 'delay_reason')
        reason_count += reason is not None
        late_reason_count += reason is not None and row['minutes'] > target
        reasons[reason or MISSING].append(row)
        contexts['shift'][_text(row.get('shift'), 'shift') or MISSING].append(row)
        contexts['traffic'][_text(row.get('traffic'), 'traffic') or MISSING].append(row)
        contexts['units_available'][_unit_band(row.get('units_available')) or MISSING].append(row)
    count = len(rows)
    late_count = sum(row['minutes'] > target for row in rows)
    reason_rows = [dict(reason=reason, count=len(group), late_count=sum(r['minutes'] > target for r in group)) for reason, group in reasons.items()]
    reason_rows.sort(key=lambda item: (-item['late_count'], -item['count'], item['reason']))
    cumulative = 0
    for item in reason_rows:
        cumulative += item['late_count']
        item['late_share'] = item['late_count'] / late_count if late_count else None
        item['cumulative_late_share'] = cumulative / late_count if late_count else None
    labels = {'shift': 'Shift', 'traffic': 'Traffic', 'units_available': 'Units available at dispatch'}
    strata = []
    for field, groups in contexts.items():
        strata.append(dict(field=field, label=labels[field], missing_count=len(groups.get(MISSING, [])),
                           groups=[dict(value=value, **_summary(group, target)) for value, group in sorted(groups.items())]))
    return dict(count=count, late_count=late_count, reason_recorded_count=reason_count,
                reason_coverage=reason_count/count if count else 0.0,
                late_reason_recorded_count=late_reason_count,
                late_reason_coverage=late_reason_count/late_count if late_count else None,
                reasons=reason_rows, strata=strata,
                warning='Recorded reasons and context comparisons are descriptive associations, not causal attribution. Missing reasons stay in denominators. Context groups pool baseline and monitoring calls and are not adjusted for priority, zone, workload, or selection bias beyond the current filters.')
