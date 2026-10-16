# Reproducible monitoring benchmark

Run `.venv/bin/python scripts/benchmark.py` from the repository root. The fixed seed, full design, numerical checks, results, Monte Carlo intervals, and source hash are in [results.json](results.json). Use `--output /tmp/benchmark.json` to avoid replacing the checked-in report. A repeat run reproduced the JSON byte-for-byte.

## Design

Primary comparisons use 200 independent replicate runs per scenario, one zone, four independent high-priority calls/day, 20 baseline days, and 25 monitoring days. Durations follow Lognormal(log(7.3),0.35), rounded to seconds. The target is eight minutes. Monitoring duration multipliers are 1.0,1.5,0.72. Both methods and raw/log options share random draws for paired comparisons. No thresholds or seeds were tuned to improve results.

The default beta-binomial method freezes a Jeffreys Beta(0.5,0.5) baseline posterior. The legacy exact-binomial method treats the observed baseline late fraction as a plug-in probability. Both use nonoverlapping seven-day periods with a separate baseline/monitoring anchor. The final four-day period is included.

A run is detected when any monitoring point signals in either direction. First detection is measured at the bin END, conditional on detection. Point fractions and run-level probabilities differ. Brackets below are Wilson 95 Monte Carlo intervals with the run as the independent unit.

## Seven-day late-fraction results

| Method | Scenario | Runs with any signal | 95% Monte Carlo interval | Median detection day, detected runs |
|---|---|---:|---:|---:|
| beta_binomial | unchanged | 2/200 (1.0%) | 0.3–3.6% | 10.5 |
| beta_binomial | slowdown_1_5x | 195/200 (97.5%) | 94.3–98.9% | 7 |
| beta_binomial | improvement_0_72x | 141/200 (70.5%) | 63.8–76.4% | 14 |
| exact_binomial | unchanged | 5/200 (2.5%) | 1.1–5.7% | 14 |
| exact_binomial | slowdown_1_5x | 200/200 (100.0%) | 98.1–100.0% | 7.0 |
| exact_binomial | improvement_0_72x | 168/200 (84.0%) | 78.3–88.4% | 7.0 |

Accounting for baseline uncertainty widens predictive limits: the lower unchanged-run signal rate comes with less power or later detection for some shifts. This is a model-based tradeoff, not a universal improvement claim. The reported predictive tail budget is conditional on the Bayesian model and prior; fixed-risk frequentist calibration is not guaranteed.

## Prespecified sensitivity cases

Each case below uses 100 independent paired-seed runs for unchanged and 1.5× slowdown, log I-MR, and seven-day bins. Cases were specified before results: one call/day,12 calls/day, repeating 1/7/3/8/2/6/4 calls/day, a five-day baseline, and stationary log-AR(1) dependence with rho 0.5. AR(1) innovations preserve the same marginal lognormal distribution. These generators deliberately test volume, reference length, and a violation of independent-call assumptions.

| Case | Scenario | Predictive signal runs | Plug-in signal runs |
|---|---|---:|---:|
| low_volume | unchanged | 0/100 | 2/100 |
| low_volume | slowdown_1_5x | 14/100 | 30/100 |
| high_volume | unchanged | 0/100 | 5/100 |
| high_volume | slowdown_1_5x | 100/100 | 100/100 |
| variable_volume | unchanged | 0/100 | 0/100 |
| variable_volume | slowdown_1_5x | 100/100 | 100/100 |
| short_baseline | unchanged | 1/100 | 9/100 |
| short_baseline | slowdown_1_5x | 70/100 | 95/100 |
| serial_dependence | unchanged | 13/100 | 21/100 |
| serial_dependence | slowdown_1_5x | 96/100 | 98/100 |

Serial dependence produces excess signals even with baseline-uncertainty integration. The model does not correct autocorrelation or changing case mix. Low volumes reduce detection power. Do not interpret the nominal tail level as a guaranteed operational alert frequency. Individual charts, multiple zones, provisional bins, and repeated looks add opportunities to signal.

## Other checks

- Raw/log I-MR and daily/seven-day comparisons for both late-rate models are retained in JSON. Four-call daily periods have little detection power.
- Independent binomial checks use direct choose(n,k) probabilities. Independent beta-binomial checks use choose(n,k)×B(k+a,n−k+b)/B(a,b), separately from the production recurrence, including uniform, all-late and zero-late cases.
- Predictive baseline points fit the posterior and are not evaluated as future predictive tests.
- I-MR can signal in an unchanged process; moving ranges are dependent and their D4 limit is not a normal 0.27% tail test. See the point/run counts in JSON.
- All 12 dataset/zone summaries now use the variable-volume field-like CSVs; synthetic labels and planted changes do not establish field performance or causation.

These experiments do not validate clinical safety, missing-arrival correction, changing staffing policies, or performance for every baseline risk and shift magnitude. They characterize the stated generators with Monte Carlo uncertainty.
