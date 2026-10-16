# Dispatch-log codebook

One row represents one ambulance dispatch with a recorded on-scene arrival. All CSVs use the same UTF-8, comma-separated header. The five columns `id`, `zone`, `priority`, `dispatched_at`, and `arrived_at` are required for analysis. `delay_reason` is optional; all bundled files include it.

| Variable | Type / allowed values | Meaning and collection source |
| --- | --- | --- |
| `id` | Unique nonempty string | Pseudonymous dispatch identifier; generated here as scenario/day/zone/call. Assign an event identifier at dispatch; never use a patient name or address. |
| `zone` | String: `North`, `Central`, `South`, `East` in demos | Operational service zone recorded at dispatch. In production use a stable, documented zone lookup. |
| `priority` | `high` or `standard` | Dispatch priority recorded before the outcome; maintain a consistent triage mapping. |
| `dispatched_at` | ISO 8601 timestamp with UTC offset; demo uses `Z` | Time the dispatch is issued, from the dispatch system clock. |
| `arrived_at` | ISO 8601 timestamp with UTC offset; demo uses `Z` | Time the unit reports on-scene arrival. Must be at or after dispatch. |
| `delay_reason` | String; empty, `traffic`, `unit_unavailable`, `access_delay` in demos | Optional operational annotation, ideally selected from a documented reason list. Empty means no reason recorded; it does not prove absence of delay. |

Derived response duration is `(arrived_at - dispatched_at)` in minutes. A late call exceeds the selected target strictly; equality is on target. Daily groups use the UTC date of dispatch. `delay_reason` is descriptive and does not establish causation. No coordinates, addresses, names, phone numbers, medical details, or patient identifiers belong in this upload format.
