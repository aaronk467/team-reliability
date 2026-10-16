# Monitoring benchmark

The default log I-MR and seven-day exact-binomial charts detect the planted changes in these simulations. They also generate chance signals under an unchanged process. This benchmark reports both outcomes; it does not claim that three-sigma limits provide a 0.27% chance of an alert over a dashboard session.

Run from the repository root, using Python 3.11 or later and no additional dependencies:

```sh
python scripts/benchmark.py
```

The command checks binomial limits against independent finite-sum calculations, runs the simulations, analyzes the three supplied CSVs, and regenerates [results.json](results.json). To explore more replicates without replacing the checked-in report:

```sh
python scripts/benchmark.py --replicates 1000 --output /tmp/responsewatch-benchmark.json
```

## Simulation design

- Seed: `4672026 + replicate`, with 200 independent replicate runs per scenario. The scenarios and chart options share random draws for a fair paired comparison.
- One zone, one priority, four independent completed calls per UTC day. Baseline: 20 days/80 calls; monitoring: 25 days/100 calls. No missing records or changes in priority mix.
- Baseline durations follow `Lognormal(mu=log(7.3), sigma=0.35)` in minutes. Durations are rounded to whole seconds, matching timestamp collection. The target is eight minutes; exactly eight minutes is on time.
- After day 20, durations are unchanged, multiplied by `1.5`, or multiplied by `0.72`. No parameter, threshold, seed, or dataset was adjusted to improve the displayed results.
- Limits are estimated from that run's baseline and frozen. The I-MR comparison uses raw minutes or log minutes. Late-fraction limits use an estimated baseline proportion and exact binomial quantiles. Seven-day bins are nonoverlapping and restart at the baseline/monitoring boundary; the last four-day monitoring bin is included.
- A run counts as detected if **any monitoring point** signals, in either direction. Individual and MR charts have 100 monitoring points per run; the seven-day late-fraction chart has four bins. Their opportunities to signal differ.
- Detection delay is the first signaled monitoring day, numbered from one. A late-fraction batch's decision date is its **end date**. Median delay is conditional on detection and excludes runs with no signals, so it must be read alongside detection probability.

## Results

Each percentage below measures the proportion of **runs with at least one monitoring signal**. Brackets are 95% Wilson intervals for Monte Carlo uncertainty, with the run as the independent unit.

| Scenario | Raw individuals | Log individuals | Seven-day late fraction | Log individuals median day, detected runs | Late fraction median day, detected runs |
|---|---:|---:|---:|---:|---:|
| Unchanged | 71.5% [64.9, 77.3] | 35.0% [28.7, 41.8] | 2.5% [1.1, 5.7] | 10 | 14 |
| Durations × 1.5 | 100% [98.1, 100] | 87.5% [82.2, 91.4] | 100% [98.1, 100] | 4 | 7 |
| Durations × 0.72 | 11.5% [7.8, 16.7] | 78.0% [71.8, 83.2] | 84.0% [78.3, 88.4] | 6 | 7 |

Under the unchanged process, the **individual point fractions** flagged were `311/20000 = 1.555%` on raw minutes and `92/20000 = 0.460%` on log minutes. Seven-day late-fraction bins flagged `5/800 = 0.625%`. These pooled fractions are descriptive; they do not treat dependent observations within a run as independent trials for confidence intervals.

The unchanged log MR chart flagged `252/20000 = 1.260%` of monitoring ranges, with at least one signal in `113/200 = 56.5%` of runs. A moving range uses adjacent observations and is dependent on neighboring ranges. Its `D4=3.267` limit is not a 0.27% normal-tail test. Under a multiplicative level change, log differences largely preserve the same distribution: log MR signaled in 57.5% of slowdown runs and 56.5% of improvement runs. Use it to examine variation, not as primary evidence of a changed response-time level.

Daily exact-binomial bins contain only four calls. They produced **zero detected runs in all three scenarios**, versus 100% and 84% detection for the slowdown and improvement with seven-day bins. Most four-call count limits cover every possible count. Aggregation improves information per assessment but delays that assessment; individual-response points remain available between batches. These are not live active-dispatch alerts.

## What these results establish

Log transformation reduces predictable upper-tail signals for a truly lognormal response-time distribution and improves sensitivity to a proportional improvement. Weekly binning solves a demonstrated loss of information from tiny daily denominators. The seven-day chart detects the slowdown by its first completed monitoring batch in the median detected run.

An unchanged process still generates many I-MR signals across repeated observations. Baseline limits are estimated from 80 calls, so the familiar known-parameter normal reference tail is not a calibrated per-observation guarantee here. Baseline estimation also explains why the exact-binomial plug-in chart can exceed its nominal known-probability tail budget. Adding charts, zones, and repeated looks increases the chance of some signal; no family-wide error guarantee is supplied. A signal calls for reviewing records and operational context rather than establishing that a process changed.

The simulation assumes independence, a common risk within a zone/priority, complete collection, a fixed call rate, and lognormal durations. Actual ambulance calls can have temporal dependence, weather/traffic changes, changing case mix, and missing arrivals. This small experiment neither estimates performance in those conditions nor validates clinical safety. Limits should be reviewed with local data before operational use. Simulation detection rates for the two chosen changes are not guarantees for smaller shifts or other baseline risks.

## Independent known-answer check

The benchmark computes `P(X=k) = choose(n,k) p^k (1-p)^(n-k)` directly and verifies the public library's integer bounds and boundary signal decisions for five binomial cases. This calculation does not call the production recurrence helper. For `n=10, p=0.5`, each extreme count has probability `1/1024 = 0.0009765625`; the central bounds are 1 and 9, and only 0 and 10 signal under the two-sided tail budget `erfc(3/sqrt(2))`. Results and probed counts are saved in the JSON. This check verifies the known-probability calculation; it does not remove uncertainty in an estimated baseline probability.

## Supplied CSVs are demonstrations, separately assessed

The supplied datasets intentionally include rare additive delays. They are **not** the uncontaminated stationary lognormal distribution above. A signal in `stable.csv` need not mean the data generator changed; it can identify a rare event or a poor distributional fit. Check the baseline-instability warnings rather than treating the word "stable" as a promise of zero signals.

With high priority, 20 baseline days, log I-MR, and seven-day late-fraction bins:

| Dataset and zone | Baseline late | Monitoring late | Monitoring individual signals | Monitoring late-fraction signals |
|---|---:|---:|---:|---:|
| `stable.csv`, South | 41.25% | 46.0% | 1/100 | 0/4 |
| `south_shift.csv`, South | 41.25% | 100.0% | 4/100 | 4/4 |
| `improvement.csv`, South | 41.25% | 6.0% | 0/100 | 3/4 |

All 12 dataset/zone summaries, baseline and monitoring denominators, percentiles, and MR counts appear in the JSON. These planted examples show what the tool displays; the independent simulation characterizes the particular statistical assumptions instead of measuring performance only on the presentation examples.
