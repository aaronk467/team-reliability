"""Public request/response contracts for the HTTP API.

The statistical library accepts ordinary dictionaries independently of FastAPI.
These models document the wire format and validate returned results so API
schema drift fails visibly instead of silently dropping calculated fields.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class DispatchRecord(BaseModel):
    """A completed, deidentified dispatch; additional logged context is retained."""

    model_config = ConfigDict(extra="allow", allow_inf_nan=False)
    id: StrictStr = Field(min_length=1, description="Unique nonpatient dispatch ID.")
    zone: StrictStr = Field(min_length=1, description="Consistently defined service area.")
    priority: StrictStr = Field(min_length=1, description="Priority assigned at dispatch.")
    dispatched_at: StrictStr = Field(description="ISO 8601 dispatch timestamp with a timezone offset.", json_schema_extra={"format": "date-time"})
    arrived_at: StrictStr = Field(description="ISO 8601 on-scene timestamp, at or after dispatch, with a timezone offset.", json_schema_extra={"format": "date-time"})
    delay_reason: StrictStr | None = Field(default=None, description="Optional recorded explanation, not a causal conclusion.")
    shift: StrictStr | None = Field(default=None, description="Optional consistently defined operational shift.")
    traffic: StrictStr | None = Field(default=None, description="Optional observed traffic category.")
    units_available: StrictInt | StrictStr | None = Field(default=None, description="Optional nonnegative count of available units at dispatch; CSV integer strings are accepted.")


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[DispatchRecord] = Field(min_length=1, max_length=100000)
    target_minutes: float = Field(default=8, gt=0, allow_inf_nan=False, strict=True, description="Strictly greater durations count as late; an agency-selected service target, not a control limit.")
    baseline_days: StrictInt = Field(default=20, ge=1, le=3650, description="Number of UTC calendar days from the first selected dispatch used to freeze limits.")
    priority: StrictStr = Field(default="all", description="Exact priority value to select, or all.")
    imr_scale: Literal["log", "raw"] = Field(default="log", description="Log transforms durations before estimating I-MR limits; individual limits are returned in minutes.")
    aggregation_days: StrictInt = Field(default=7, ge=1, le=365, description="Nonoverlapping late-rate periods, restarted at the baseline boundary.")
    p_method: Literal["beta_binomial", "exact_binomial"] = Field(default="beta_binomial", description="Beta-binomial posterior predictive limits account for estimated baseline risk; exact-binomial uses a plug-in baseline probability.")


class HealthResponse(ResponseModel):
    status: Literal["ok"]


class DatasetInfo(ResponseModel):
    name: str
    filename: str


class DatasetResponse(ResponseModel):
    name: str
    records: list[DispatchRecord]


class ValidatedRecord(DispatchRecord):
    minutes: float = Field(ge=0, allow_inf_nan=False, description="Calculated arrival minus dispatch duration in minutes.")


class Summary(ResponseModel):
    count: int = Field(ge=1)
    late_count: int = Field(ge=0)
    late_rate: float = Field(ge=0, le=1)
    late_ci_low: float = Field(ge=0, le=1, description="Lower Wilson 95% interval bound for the observed late probability.")
    late_ci_high: float = Field(ge=0, le=1, description="Upper Wilson 95% interval bound for the observed late probability.")
    p90_minutes: float = Field(ge=0, description="Empirical 90th percentile using Hyndman–Fan type 7 interpolation.")


class Comparison(ResponseModel):
    baseline: Summary | None
    monitoring: Summary | None
    late_rate_delta_pp: float | None = Field(description="Monitoring minus baseline late proportion, in percentage points; descriptive rather than causal.")
    p90_delta_minutes: float | None


class IndividualPoint(ResponseModel):
    id: str
    dispatched_at: str
    minutes: float = Field(ge=0)
    in_baseline: bool
    signal: bool
    moving_range: float | None = Field(ge=0)
    mr_signal: bool


class IMRChart(ResponseModel):
    center: float | None
    lcl: float | None
    ucl: float | None
    mr_center: float | None
    mr_ucl: float | None
    scale: Literal["log", "raw"]
    mr_units: Literal["log ratio", "minutes"]
    points: list[IndividualPoint]


class PeriodPoint(ResponseModel):
    date: str
    period_start: str
    period_end: str
    n: int = Field(ge=1)
    late_count: int = Field(ge=0)
    proportion: float = Field(ge=0, le=1)
    lcl: float | None
    ucl: float | None
    lcl_count: int | None
    ucl_count: int | None
    in_baseline: bool
    signal: bool
    signal_evaluated: bool = Field(description="False for fitted predictive-baseline periods and whenever reference data are unavailable.")


class LateRateChart(ResponseModel):
    center: float | None
    baseline_late_rate: float | None
    method: Literal["beta_binomial", "exact_binomial"]
    alpha: float = Field(gt=0, lt=1)
    prior_alpha: float | None
    prior_beta: float | None
    posterior_alpha: float | None
    posterior_beta: float | None
    posterior_mean: float | None
    baseline_signal_policy: Literal["not_evaluated_fitted_reference", "descriptive_diagnostic"]
    aggregation_days: int = Field(ge=1)
    points: list[PeriodPoint]


class BaselineQuality(ResponseModel):
    baseline_count: int = Field(ge=0)
    i_signals: int = Field(ge=0)
    mr_signals: int = Field(ge=0)
    p_signals: int | None = Field(ge=0)
    imr_limits_available: bool
    review_recommended: bool
    reasons: list[str]


class DelayReason(ResponseModel):
    reason: str
    count: int = Field(ge=1)
    late_count: int = Field(ge=0)
    late_share: float | None = Field(ge=0, le=1)
    cumulative_late_share: float | None = Field(ge=0, le=1)


class ContextGroup(Summary):
    value: str


class ContextStratum(ResponseModel):
    field: Literal["shift", "traffic", "units_available"]
    label: str
    missing_count: int = Field(ge=0)
    groups: list[ContextGroup]


class DelayPatterns(ResponseModel):
    count: int = Field(ge=1)
    late_count: int = Field(ge=0)
    reason_recorded_count: int = Field(ge=0)
    reason_coverage: float = Field(ge=0, le=1)
    late_reason_recorded_count: int = Field(ge=0)
    late_reason_coverage: float | None = Field(ge=0, le=1)
    reasons: list[DelayReason]
    strata: list[ContextStratum]
    warning: str


class ZoneAnalysis(Summary):
    zone: str
    baseline_count: int = Field(ge=0)
    warnings: list[str]
    comparison: Comparison
    imr: IMRChart
    p_chart: LateRateChart
    baseline_quality: BaselineQuality
    delay_patterns: DelayPatterns


class AnalysisResponse(ResponseModel):
    summary: Summary
    comparison: Comparison
    zones: list[ZoneAnalysis]
    target_minutes: float = Field(gt=0)
    baseline_days: int = Field(ge=1)
    baseline_start: str
    baseline_end: str
    priority: str
    imr_scale: Literal["log", "raw"]
    aggregation_days: int = Field(ge=1)
    p_method: Literal["beta_binomial", "exact_binomial"]
    warnings: list[str]
    delay_patterns: DelayPatterns
