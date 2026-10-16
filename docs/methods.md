# Statistical methods and interpretation

Analyze one priority at a time when operationally meaningful. Calls are ordered by dispatch timestamp within each zone. All durations and targets are in minutes. The first `baseline_days` UTC calendar days beginning at the earliest eligible dispatch define the fixed reference period; subsequent calls are monitored against that reference. Filtering, target selection, and reference selection change the analysis and must be recorded with a report.

## Individuals and moving-range charts

For baseline durations x₁,…,xₘ, the individuals center is the arithmetic mean. Consecutive absolute differences MRᵢ = |xᵢ − xᵢ₋₁| estimate within-process variation: sigma = mean(MR) / 1.128. Individuals limits are mean ± 3 sigma, with a nonnegative lower duration limit. The moving-range center is mean(MR), lower limit zero, and upper limit 3.267 × mean(MR). Monitor each later observation using these frozen limits. A point outside the limits warrants investigation, not an automatic verdict on a dispatcher. Zero estimated variation leaves I-MR limits unavailable and produces a warning; more representative baseline data are needed.

## Daily late fractions

A call is late when duration is strictly greater than the selected target. For each zone and dispatch day, p = late calls / completed eligible calls. The baseline center p̄ pools the baseline late counts and denominators; it is not an unweighted average of daily percentages. For daily sample size n, limits are p̄ ± 3 sqrt[p̄(1−p̄)/n], clipped to [0,1]. Limits therefore vary with the daily denominator. No calls means no estimate, not a zero late rate. When the baseline has no late calls or all calls late, nominal limits collapse and cannot establish safety. Small counts make normal-approximation p-chart limits coarse.

## Risk summaries

Report the observed late fraction with a two-sided 95% Wilson score interval using z = 1.959963984540054. For k late calls among n completed calls, center = (k/n + z²/(2n))/(1+z²/n), and half-width = z sqrt[(k/n)(1−k/n)/n + z²/(4n²)]/(1+z²/n). The interval describes binomial sampling uncertainty under independence; it does not account for missing calls, correlated responses, or selection bias. Empirical p90 is the linearly interpolated sample 90th percentile, not a guaranteed bound on future calls.

## Limits of the analysis

Response times are often right-skewed; conventional I-MR limits can have different false-alarm behavior from a normal process. Consecutive calls and days can be autocorrelated, and overlapping crews or demand surges violate independence. Zone/priority case mix, geography, staffing, seasonality, and changing recording practice may explain differences. Multiple charts and repeated reviews increase the chance of chance signals. Tiny groups need more data; a point estimate or overlapping interval alone does not establish equivalence or a difference.

Control limits describe baseline variation; the target describes an operational expectation. A statistically stable process may still miss its target. No Cp/Cpk is reported because this skewed, one-sided response-time setting does not justify a normal two-sided capability calculation. No fitted lifetime reliability, MTTF, patient risk, causal attribution, or clinical benefit is claimed. Use signals to prioritize a source-record and operational investigation, then evaluate any intervention prospectively.
