# Dispatch-log codebook

One row represents one ambulance dispatch with a recorded on-scene arrival. All CSVs use the same UTF-8, comma-separated header. The five columns `id`, `zone`, `priority`, `dispatched_at`, and `arrived_at` are required for analysis. `delay_reason`, `shift`, `traffic`, and `units_available` are optional; all bundled files include them. Optional context values may be blank when unknown.

| Variable | Type / allowed values | Meaning and collection source |
| --- | --- | --- |
| `id` | Unique nonempty string | Pseudonymous dispatch identifier; generated here as scenario/day/zone/call. Assign an event identifier at dispatch; never use a patient name or address. |
| `zone` | String: `North`, `Central`, `South`, `East` in demos | Operational service zone recorded at dispatch. In production use a stable, documented zone lookup. |
| `priority` | `high` or `standard` | Dispatch priority recorded before the outcome; maintain a consistent triage mapping. |
| `dispatched_at` | ISO 8601 timestamp with UTC offset; demo uses `Z` | Time the dispatch is issued, from the dispatch system clock. |
| `arrived_at` | ISO 8601 timestamp with UTC offset; demo uses `Z` | Time the unit reports on-scene arrival. Must be at or after dispatch. |
| `shift` | `day` or `night`; blank if unknown | Shift at dispatch. Demo uses day 07:00–18:59 UTC; night otherwise. Real agencies should document their own shift mapping. |
| `traffic` | `light`, `moderate`, `heavy`; blank if unknown | Coarse traffic category observed or estimated at dispatch. Use a consistent source and documented category definitions. |
| `units_available` | Nonnegative integer, demo 0–4; blank if unknown | Dispatch-system count of available units at dispatch, with service-area and eligibility definitions documented. Zero is a measured count, not missing. |
| `delay_reason` | String; empty, `traffic`, `unit_unavailable`, `access_delay` in demos | Optional operational annotation, ideally selected from a documented reason list. Empty means no reason recorded; it does not prove absence of delay. |

Derived response duration is `(arrived_at - dispatched_at)` in minutes. A late call exceeds the selected target strictly; equality is on target. Daily groups use the UTC date of dispatch. `delay_reason` is descriptive and does not establish causation. No coordinates, addresses, names, phone numbers, medical details, or patient identifiers belong in this upload format.

Optional context is preserved in CSV export. Unknown values must remain distinguishable from measured zero or a recorded no-delay assessment. Context strata and reason summaries are descriptive associations; they do not adjust for confounding or establish why a response was late.
