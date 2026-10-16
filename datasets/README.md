# Demonstration data

These are fictional dispatch logs, generated with Python's standard library and seed 467. They contain no patient information and support no clinical or operational performance claims. Reproduce every CSV from the repository root with `python datasets/generate.py`.

| File | Rows | Scenario |
| --- | ---: | --- |
| `stable.csv` | 1,440 | A roughly stable, right-skewed response process with occasional long delays. Random control-chart signals remain possible. |
| `south_shift.csv` | 1,440 | Same underlying calls, with five minutes added to South responses from January 21 onward. |
| `improvement.csv` | 1,440 | Same underlying calls, with response duration multiplied by 0.72 in all zones from January 21 onward. |

Each file spans January 1–February 14, 2026, with eight dispatched calls per zone per day: four high priority and four standard priority. January 1–20 is the reference period; January 21–February 14 is the monitoring period. These balanced counts simplify the demo; real demand, case mix, and missingness will vary. Dispatches are randomly distributed over each UTC day, and arrivals may occur the following day. Aggregation uses dispatch date. Files share a random stream so scenario differences are easy to inspect; they are not three independent samples.

Response times use a lognormal multiplier, priority-specific centers, small zone differences, and occasional additional delays. This is illustrative operational variation, not a model estimated from ambulance services. `south_shift` adds a late-period process shift, not a time-of-day night shift. The default eight-minute target is a demonstration choice, not a medical recommendation. Filter to high priority for the primary comparison; standard-priority calls have a deliberately different distribution.

See [CODEBOOK.md](CODEBOOK.md) for field definitions and [collection.md](../docs/collection.md) for a prospective collection protocol.
