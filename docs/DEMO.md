# Five-minute judge walkthrough

Open [ResponseWatch](https://responsewatch-lpj2.onrender.com). Use **High** priority, an **8-minute** target, the first **20 UTC days** as baseline, **log** I-MR, and **7-day** late-fraction bins. These settings are part of the analysis, not clinical recommendations. Select **South**. All observations are synthetic.

## 1. Establish the reference

Select `stable`. The reference is January 1–20, 2026; monitoring is January 21–February 14. South has 80 high-priority baseline calls and 100 monitoring calls. Show the shaded baseline, geometric-mean center, back-transformed individual limits in minutes, and moving ranges in log-ratio units. The target line describes service performance; control limits describe baseline variation. The stable scenario still has late calls and occasional unusual observations.

## 2. Reveal a planted deterioration

Select `south_shift`, retaining the same settings and South zone. The generator adds five minutes to South calls after the reference period; the data are paired across scenarios for a transparent demonstration. Compare the before/after summary, Wilson intervals, empirical p90, investigation queue, and exact-binomial period signals. The process can clearly worsen even though many individual calls remain inside broad I-chart limits.

## 3. Show the improvement scenario

Select `improvement`. After the reference period, the generator multiplies durations by 0.72. Show the lower monitoring risk and p90, together with low-side period signals. This is a known simulated change, not evidence that a real intervention caused an improvement. Keep the original baseline frozen during the demonstration.

### Expected South results

The common South baseline is **33/80 late (41.25%)**, Wilson 95% interval **31.11–52.20%**, p90 **10.75 minutes**. The table covers only monitoring calls, and counts only monitoring-period signals. Results are rounded for presentation.

| Scenario | Monitoring late risk (Wilson 95% interval) | Monitoring p90, min | Change in late risk, pp | Change in p90, min | I / MR / period signals |
| --- | --- | ---: | ---: | ---: | --- |
| `stable` | 46/100 = 46.00% (36.56–55.74%) | 10.56 | +4.75 | −0.19 | 1 / 0 / 0 |
| `south_shift` | 100/100 = 100.00% (96.30–100.00%) | 15.56 | +58.75 | +4.81 | 4 / 0 / 4 |
| `improvement` | 6/100 = 6.00% (2.78–12.48%) | 7.61 | −35.25 | −3.15 | 0 / 0 / 3 |

The baseline has two moving-range signals in these South examples. Explicitly show the instability warning: baseline representativeness must be investigated before operational use. Do not remove inconvenient observations solely to tighten limits. The synthetic stable label means the generator's distribution does not change over time; it does not promise a signal-free chart or an operationally acceptable process.

The four monitoring bins cover January 21–27, January 28–February 3, February 4–10, and February 11–14, with 28, 28, 28, and 16 high-priority South calls respectively. Binomial limits account for these observed denominators. Switch to one-day bins to illustrate why four calls per day provide weak detection power: no daily signal does not establish acceptable service. Binomial limits use estimated baseline risk, so the nominal three-sigma tail probability is not a calibrated predictive guarantee.

## 4. Demonstrate collection and unresolved calls

In the dispatch log, start an open dispatch with a nonpatient ID and a valid recent timestamp. Show its elapsed time and the active/overdue counts. These calls are deliberately separate from completed-call statistics and CSV export. Record a valid arrival; the call then joins completed-call analysis. Explain that unresolved-call exclusion can make the completed-call results look better than the full operational picture.

This register is browser-local and source-specific. It does not synchronize among dispatchers or send background emergency alerts. Use only synthetic entries. For a clean repeat of the expected table, use an unmodified demo in a fresh browser profile; locally saved additions change the results.

## Reproduce the table in Python

From an installed repository environment:

```python
import csv
from responsewatch.stats import analyze

for name in ("stable", "south_shift", "improvement"):
    with open(f"datasets/{name}.csv", newline="") as handle:
        records = list(csv.DictReader(handle))
    result = analyze(records, target_minutes=8, baseline_days=20,
                     priority="high", imr_scale="log", aggregation_days=7)
    south = next(zone for zone in result["zones"] if zone["zone"] == "South")
    print(name, south["comparison"])
    print("I", sum(p["signal"] and not p["in_baseline"]
                   for p in south["imr"]["points"]),
          "MR", sum(p["mr_signal"] and not p["in_baseline"]
                    for p in south["imr"]["points"]),
          "period", sum(p["signal"] and not p["in_baseline"]
                        for p in south["p_chart"]["points"]))
```

See [methods](methods.md), [collection protocol](collection.md), and the [validation record](VALIDATION.md) for assumptions and the version/checks actually verified.
