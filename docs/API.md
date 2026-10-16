# API reference

All endpoints are under `/api`. Times normalize to ISO 8601 UTC offsets; durations are minutes, proportions are fractions from 0 to 1. Invalid analysis or record inputs return HTTP 422 with `detail` explaining the error. Structural request validation can return FastAPI's list of field errors. Unknown dataset names return 404.

| Endpoint | Input | Successful JSON output |
| --- | --- | --- |
| `GET /api/health` | None | `{"status":"ok"}` |
| `GET /api/datasets` | None | Array of objects with `name` and `filename`. |
| `GET /api/datasets/{name}` | A listed dataset name without `.csv` | Object with `name` and `records` (array of dispatch record objects). |
| `POST /api/validate-record` | One dispatch record object | Validated record, with normalized timestamp strings and derived `minutes`. This validates one record, not dataset-wide ID uniqueness. |
| `POST /api/analyze` | `records`, optional `target_minutes` (8), `baseline_days` (20), `priority` (`all`), `imr_scale` (`log`), `aggregation_days` (7) | Analysis object detailed below. Extra top-level fields are rejected. `imr_scale` must be `log` or `raw`; `aggregation_days` must be an integer from 1 to 365; `baseline_days` must be an integer from 1 to 3650; the target must be finite and positive. |

Records require nonempty string `id`, `zone`, and `priority`, plus timezone-aware string `dispatched_at` and `arrived_at`. `delay_reason` is optional and may be a string or null. Arrival must not precede dispatch. IDs must be unique in an analysis request. There must be 1–100,000 records; at least one must match the chosen priority. Zones and priorities can use operational labels beyond the demo labels; the priority filter is exact and `all` selects every priority. Validated records preserve additional input fields, so do not submit sensitive fields.

## Analysis response

Top-level fields are `summary`, `zones`, `target_minutes`, `baseline_days`, `baseline_start`, `baseline_end`, `priority`, `imr_scale`, `aggregation_days`, `comparison`, and `warnings`. Baseline dates are inclusive UTC dates; warnings are strings. `summary` covers all completed calls matching the priority filter, across the entire uploaded period.

A summary contains `count`, `late_count`, `late_rate`, `late_ci_low`, `late_ci_high`, and `p90_minutes`. The interval is Wilson 95%; p90 is linearly interpolated. Each element of `zones` has `zone`, the same summary fields, `baseline_count`, `comparison`, `warnings`, `imr`, and `p_chart`.

`comparison` contains `baseline` and `monitoring` (each a summary or null), `late_rate_delta_pp` (monitoring minus baseline in percentage points), and `p90_delta_minutes` (monitoring minus baseline in minutes). Deltas are null when either phase is empty. They are descriptive, not causal estimates or tests of intervention effect.

`imr` contains `center`, `lcl`, `ucl`, `mr_center`, `mr_ucl`, `scale`, `mr_units`, and `points`. Each point contains `id`, `dispatched_at`, `minutes`, `in_baseline`, `signal`, `moving_range`, and `mr_signal`. The first moving range is null. `center`, `lcl`, and `ucl` are always in minutes. With `scale="log"`, the center is a back-transformed log mean (geometric mean); moving-range values use `mr_units="log ratio"`. With `scale="raw"`, moving ranges use `mr_units="minutes"`. Log analysis cannot estimate limits with a zero baseline duration; no artificial offset is added. Limits are null when the baseline cannot support the estimate, including constant baseline durations. `signal` tests an individuals point strictly outside its limits; `mr_signal` tests a moving range above its upper limit. Signals are computed for baseline and monitoring points; use `in_baseline` to distinguish them. The moving-range lower limit is zero.

`p_chart` contains `center` (pooled baseline late fraction), `method` (`exact_binomial`), `alpha` (0.002699796063260207), `aggregation_days`, and `points`. Each point contains `date` (period start), `period_start`, `period_end`, `n`, `late_count`, `proportion`, `lcl`, `ucl`, `lcl_count`, `ucl_count`, `in_baseline`, and `signal`. Count limits are binomial quantiles; proportion limits divide them by n. A signal requires a count strictly outside its limits. These limits use an estimated baseline p and do not guarantee calibrated predictive false-alarm rates.

Bins are nonoverlapping and anchored separately at baseline and monitoring start; they never cross the boundary. Seven-day aggregation is the default; one-day aggregation is optional. Partial bins use their actual dates and sample sizes; periods without observed completed calls are omitted. Limits are null if the zone has no baseline calls. Degenerate baseline fractions of 0 or 1 produce a warning.

Read [methods](methods.md) before interpreting signals. These are completed-call summaries, not estimates corrected for unresolved calls or case mix.

Open dispatches are a separate browser-local workflow, not an API persistence resource. Do not send missing or invented arrivals to `/api/analyze`; record an arrival before a call joins the completed-call analysis.
