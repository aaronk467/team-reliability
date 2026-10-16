# Statistical methods and interpretation

Analyze comparable priorities separately. Calls are ordered by dispatch timestamp and ID within each zone. All target values and response durations are minutes. The first `baseline_days` UTC calendar days beginning at the earliest eligible dispatch define the fixed reference period; later calls form the monitoring period. Freeze this reference before monitoring. Filtering, target, reference length, I-MR scale, and aggregation length are analysis choices and must accompany a report.

## Individuals and moving-range charts

The default is log-scale I-MR because response durations are positive and often right-skewed. Set yᵢ = ln(xᵢ) for duration xᵢ. The baseline center on the transformed scale is mean(y). Consecutive absolute differences MRᵢ = |yᵢ − yᵢ₋₁| estimate within-process variation: sigma = mean(MR) / 1.128. Individual limits on the transformed scale are mean(y) ± 3 sigma. The dashboard back-transforms the center and limits with exp(), so the displayed center is a **geometric mean**, and the asymmetric limits are in minutes. Moving ranges and their center remain in **log-ratio units**, with lower limit zero and upper limit 3.267 × mean(MR).

The `raw` option applies the same I-MR formulas directly to durations: arithmetic-mean center, mean ± 3 mean(MR)/1.128 individual limits (lower limit clipped at zero), and moving ranges in minutes. The choice must be made for the process, rather than selected to obtain desired signals. A log transform does not guarantee normality or independence. Successive changes can cross the baseline/monitoring boundary, but baseline estimation uses baseline calls only.

Signals are single observations strictly outside frozen limits; other run rules are not applied. Baseline signals prompt review of whether the reference period is stable. Two baseline calls are the computational minimum, not adequate operational validation. Zero estimated variation leaves I-MR limits unavailable. Zero durations cannot be logged: no arbitrary offset is added and no observations are silently excluded to fit a log model. A zero baseline duration disables log limits; a zero monitoring duration has no transformed moving range and produces a warning. Investigate timestamp precision or use a justified raw-scale analysis.

## Aggregated late fractions and exact-binomial limits

A call is late when duration is strictly greater than the selected target. The baseline center p̄ pools baseline late counts and completed-call denominators; it is not an unweighted mean of period percentages. The default uses nonoverlapping **seven-day bins**, separately anchored at baseline start and monitoring start. A bin never crosses the reference boundary. Final partial bins retain their observed sample size n and are labeled with their actual dates. A one-day option supports finer review but may have very little power with sparse calls. No calls means no estimate, not a zero late rate.

For each bin, model K ~ Binomial(n, p̄). Count limits are the lower quantiles Q(α/2) and Q(1−α/2), where Q(q) is the smallest integer k with P(K≤k) ≥ q and α = 0.002699796063260207 (the conventional two-sided three-sigma tail probability). Displayed proportion limits divide these count limits by n. A signal requires the observed count to be **strictly outside** the discrete limits. Exact-binomial limits avoid the sparse-count normal approximation; discreteness can make them conservative, and some low-volume groups cannot signal at all.

Here p̄ is estimated from the baseline. The nominal known-probability binomial tail bound is **not a calibrated predictive false-alarm guarantee** after estimating p, or under autocorrelation, changing case mix, or repeated testing. An all-on-time or all-late baseline yields degenerate limits and a warning; collect more representative baseline data and consider a fuller uncertainty model. Aggregating increases the sample size per point but delays detection and does not remove dependence.

## Risk summaries and before/after comparisons

Overall and per-zone summaries report count, late count, late fraction, Wilson 95% interval, and empirical p90. Separate baseline and monitoring summaries support comparison without mixing the two phases. The late-risk delta is **monitoring minus baseline in percentage points**, not relative percent; the p90 delta is monitoring minus baseline in minutes. These deltas are descriptive, with no causal interpretation or formal difference-test confidence interval. Empty phases return null summaries/deltas.

Wilson intervals use z = 1.959963984540054. For k late calls among n completed calls, p = k/n, center = (p + z²/(2n))/(1+z²/n), and half-width = z sqrt[p(1−p)/n + z²/(4n²)]/(1+z²/n). This interval describes binomial sampling uncertainty under independence; it does not correct for missing calls, correlated responses, or selection bias. Empirical p90 uses linear interpolation at position 0.9(n−1) in the sorted sample (Hyndman–Fan type 7). It is not a guaranteed bound on future calls.

## Limits of the analysis

Consecutive calls and bins can be autocorrelated, and shared crews or demand surges violate independence. Zone/priority case mix, geography, staffing, seasonality, and changing recording practice may explain differences. Multiple charts and repeated reviews increase chance signals. Tiny groups need more data; overlapping confidence intervals alone establish neither equivalence nor a difference. Normality of transformed residuals and representativeness of the baseline require operational evaluation beyond these demonstrations.

Control limits describe baseline variation; the target describes an operational expectation. A stable process may still miss its target. No Cp/Cpk is reported because a normal, two-sided capability calculation is not justified here. No fitted lifetime reliability, MTTF, patient risk, causal attribution, or clinical benefit is claimed. Investigate source records and operational context, then evaluate interventions prospectively. Open calls are tracked separately in the browser and are not completed-call observations; their exclusion can bias apparent current performance downward.
