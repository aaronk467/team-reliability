# API reference

All endpoints are under `/api`. Times normalize to ISO 8601 UTC offsets; durations are minutes, proportions are fractions from 0 to 1. Invalid analysis or record inputs return HTTP 422 with `detail` explaining the error. Structural request validation can return FastAPI's list of field errors. Unknown dataset names return 404.

| Endpoint | Input | Successful JSON output |
| --- | --- | --- |
| `GET /api/health` | None | `{"status":"ok"}` |
| `GET /api/datasets` | None | Array of objects with `name` and `filename`. |
| `GET /api/datasets/{name}` | A listed dataset name without `.csv` | Object with `name` and `records` (array of dispatch record objects). |
| `POST /api/validate-record` | One dispatch record object | Validated record, with normalized timestamp strings and derived `minutes`. This validates one record, not dataset-wide ID uniqueness. |
| `POST /api/analyze` | `records`, optional `target_minutes` (8), `baseline_days` (20), `priority` (`all`), `imr_scale` (`log`), `aggregation_days` (7), `p_method` (`beta_binomial`) | Analysis object detailed below. Extra top-level fields are rejected. `imr_scale` must be `log` or `raw`; `aggregation_days` must be an integer from 1 to 365; `baseline_days` must be an integer from 1 to 3650; the target must be finite and positive. |

Records require nonempty string `id`, `zone`, and `priority`, plus timezone-aware string `dispatched_at` and `arrived_at`. `delay_reason` is optional and may be a string or null. Arrival must not precede dispatch. IDs must be unique in an analysis request. There must be 1–100,000 records; at least one must match the chosen priority. Zones and priorities can use operational labels beyond the demo labels; the priority filter is exact and `all` selects every priority. Validated records preserve additional input fields, so do not submit sensitive fields.

## Analysis response

Top-level fields are `summary`, `zones`, `target_minutes`, `baseline_days`, `baseline_start`, `baseline_end`, `priority`, `imr_scale`, `aggregation_days`, `p_method`, `comparison`, `delay_patterns`, and `warnings`. Baseline dates are inclusive UTC dates; warnings are strings. `summary` covers all completed calls matching the priority filter, across the entire uploaded period.

A summary contains `count`, `late_count`, `late_rate`, `late_ci_low`, `late_ci_high`, and `p90_minutes`. The interval is Wilson 95%; p90 is linearly interpolated. Each element of `zones` has `zone`, the same summary fields, `baseline_count`, `comparison`, `warnings`, `imr`, and `p_chart`.

`comparison` contains `baseline` and `monitoring` (each a summary or null), `late_rate_delta_pp` (monitoring minus baseline in percentage points), and `p90_delta_minutes` (monitoring minus baseline in minutes). Deltas are null when either phase is empty. They are descriptive, not causal estimates or tests of intervention effect.

`imr` contains `center`, `lcl`, `ucl`, `mr_center`, `mr_ucl`, `scale`, `mr_units`, and `points`. Each point contains `id`, `dispatched_at`, `minutes`, `in_baseline`, `signal`, `moving_range`, and `mr_signal`. The first moving range is null. `center`, `lcl`, and `ucl` are always in minutes. With `scale="log"`, the center is a back-transformed log mean (geometric mean); moving-range values use `mr_units="log ratio"`. With `scale="raw"`, moving ranges use `mr_units="minutes"`. Log analysis cannot estimate limits with a zero baseline duration; no artificial offset is added. Limits are null when the baseline cannot support the estimate, including constant baseline durations. `signal` tests an individuals point strictly outside its limits; `mr_signal` tests a moving range above its upper limit. Signals are computed for baseline and monitoring points; use `in_baseline` to distinguish them. The moving-range lower limit is zero.

`p_chart` includes `center`, `baseline_late_rate`, `method`, `alpha`, `aggregation_days`, prior/posterior parameters, `posterior_mean`, `baseline_signal_policy`, and period `points`. Each point includes date/start/end, observed n and late count/proportion, count/proportion limits, `in_baseline`, `signal_evaluated`, and `signal`. The default method is `beta_binomial`: prior Beta(0.5,0.5), frozen posterior Beta(k+0.5,m−k+0.5), future count BetaBinomial(n,a,b). The center is the posterior mean; the observed baseline rate is separate. Fitted baseline periods are not evaluated as predictive tests. The legacy `exact_binomial` option uses a plug-in baseline probability. Neither model guarantees fixed-risk frequentist false-alarm calibration.

`baseline_quality` per zone reports count, I/MR diagnostic counts, nullable p diagnostic count, I-MR availability, review recommendation and reasons. This is a review prompt, not certification of stationarity.

`delay_patterns` at overall and zone level contains all/late reason coverage, a Pareto-ordered `reasons` list (reason, total count, late count, share of ALL late calls and cumulative share), and `strata` for shift/traffic/available units. Each stratum supplies missing_count and groups with value, count, late count/risk, Wilson interval and p90. Units use 0,1,2,3+ bands; missing context remains Not recorded. Invalid noninteger/negative unit counts are rejected. These are unadjusted all-period associations, not causal or intervention effects.

Periods never cross the baseline boundary. Final partial bins use observed n; empty periods are omitted. No baseline data means null limits. Both prior and posterior are fixed during monitoring; later calls cannot revise reference risk.

Read [methods](methods.md) before interpreting signals. These are completed-call summaries, not estimates corrected for unresolved calls or case mix.

Open dispatches are a separate browser-local workflow, not an API persistence resource. Do not send missing or invented arrivals to `/api/analyze`; record an arrival before a call joins the completed-call analysis.

## Worked request and response

Request `POST /api/analyze` with `{"records":[{"id":"example-1","zone":"North","priority":"high","dispatched_at":"2026-01-01T12:00:00Z","arrived_at":"2026-01-01T12:09:00Z"}],"priority":"high","p_method":"beta_binomial"}`. This single observation illustrates schema only; it cannot establish reliable I-MR limits. A complete actual JSON response is committed in [example-response.json](example-response.json).

## Optional resolution review API

`GET /api/reviews/config` returns public capability metadata only. If shared mode is configured, `GET /api/reviews?source=stable` and `PUT /api/reviews` require `Authorization: Bearer <operator-provided token>`. Never place the token in a URL or commit it. Both reads and writes are protected. Disabled mode returns503; invalid authentication401; stale versions409; invalid review fields422.

A PUT body contains `source`, `zone`, `owner` (nonpersonal alias), `status` (`open`, `in_progress`, `resolved`), `action`, nullable ISO `due_date`, and `version` (zero for a new record). Read the latest version before updating. Progressed reviews require an owner; resolved reviews require an action. Successful writes return the new version and UTC `updated_at`. SQLite writes are transactional and prevent silent overwrites. Dispatch records are not persisted by this API.
