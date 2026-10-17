# Five-minute judge walkthrough

Open [ResponseWatch](https://responsewatch-lpj2.onrender.com) with High priority, an 8-minute illustrative target, the first 20 UTC days as baseline, log I-MR, seven-day periods, and **beta-binomial predictive** limits. Select South. Use a fresh browser profile for the unmodified expected results; saved additions change the analysis.

Start in **Key statistics** for the purpose guide, main performance measures, zone comparisons, charts, and qualitative fault tree. **Dispatch workspace** groups the call-logging and follow-up tools. **Supporting analysis** holds the detailed context, baseline diagnostics, and period/model information. Dataset/settings stay shared across these views; **Methods & guidance** remains available for interpretation.

## Reference and known changes

Each of the three synthetic CSVs has 1,781 completed calls across four zones over January 1–February 14, 2026, including 845 high-priority calls. Daily volumes, priority mix, time of day, traffic and available units vary. The first 20 calendar days are the reference; monitoring begins January 21.

South's high-priority baseline has 48/103 late calls (46.60%), Wilson 95% interval 37.26–56.18%, and p90 10.68 min. Show the frozen reference and charts in Key statistics, then use Supporting analysis to inspect the observed baseline proportion, posterior predictive mean, Jeffreys prior, and baseline-quality panel. A warning calls for investigation; it does not certify the baseline as suitable.

| Scenario | Monitoring late calls | Monitoring p90 | Risk change, percentage points | I / MR / predictive period signals |
|---|---:|---:|---:|---:|
| stable | 50/107 (46.73%) | 10.84 min | +0.13 | 0 / 0 / 0 |
| south_shift | 107/107 (100.00%) | 15.84 min | +53.40 | 1 / 0 / 4 |
| improvement | 10/107 (9.35%) | 7.80 min | -37.26 | 3 / 0 / 2 |

## Demonstration order

1. In **Key statistics**, select stable: distinguish routine reference variation, service-target performance, and an out-of-limit statistical signal. Use the qualitative fault tree to introduce possible paths for investigation; its branches are prompts, not proven causes or calculated probabilities.
2. Select south_shift: the generator adds 5 minutes to South calls after day 20. Show the baseline/monitoring difference and four predictive deterioration signals.
3. Select improvement: durations multiply by 0.72 after day 20. Show lower monitoring late risk, p90, and low-side predictive signals. These are planted outcomes, not estimates of a real intervention's causal effect.
4. Open **Dispatch workspace**. Start an open dispatch using a nonpatient ID. Demonstrate elapsed/overdue status, reload persistence, and arrival recording. Completed denominators change only after valid arrival. Show Log completed call as the alternative for a call with both timestamps already known. Select a completed record to inspect its response against its zone's baseline limits and service target; distinguish that comparison from the separate outside-limit call list.
5. In the same workspace's Resolution review, assign a synthetic reviewer alias, action, status and follow-up date. Demonstrate local save/export. Shared server mode requires an operator-configured token and persistent database path; the free public host defaults to browser-local mode.
6. Open **Supporting analysis**. In Delay patterns, compare annotation coverage and Pareto shares. Unknown reasons remain in denominators. Expand shift/traffic/units groups and explain counts, Wilson intervals, confounding, and missing context. Inspect baseline quality and detailed period/model information when explaining a signal. Finish with **Methods & guidance** for assumptions.

## Questions to answer

- Why predictive limits? They integrate finite-baseline risk uncertainty under a declared prior and model. They do not automatically correct dependence or guarantee fixed-risk false-alarm rates.
- Why seven-day periods? Aggregation improves information per assessment but delays detection. Daily groups remain available, and partial periods are provisional.
- Why log times? Positive durations are often right-skewed; log I-MR addresses multiplicative variation while still requiring baseline/independence review.
- Why no clinical claims? No patient outcomes are collected. The tool supports operational quality investigation.

Show the 56-test suite documented in [VALIDATION.md](VALIDATION.md), full typed [API documentation](API.md), and the prespecified [benchmark](../benchmarks/README.md). The [collection protocol](collection.md) explains how to gather and audit real data. The tab organization changes presentation; the statistical engine and known dataset outcomes remain unchanged.
