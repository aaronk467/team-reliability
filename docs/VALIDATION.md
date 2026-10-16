# Validation record

## Version 0.3 local verification

Environment: Python 3.12.14, Node 24.19.0, npm 11.9.0, system Chromium. The install script completed pinned dependency installation, the locked React/Vite production build, and **56 passing tests**.

The statistical tests use independently known log I-MR values, direct binomial and beta-function finite sums, uniform beta-binomial probabilities, boundary signal decisions, 100,000-call stability, and zero/all-late baselines. They verify that monitoring data cannot change the reference posterior or limits and that predictive baseline points are not presented as out-of-sample tests.

API tests compare the entire typed response to library results, retain optional fields, reject invalid context/settings, and inspect nested OpenAPI schemas. Delay-pattern tests keep missing reasons in denominators and distinguish measured zero units from missing data. Dataset tests regenerate all three files into a temporary directory and compare exact bytes, record validity, variable demand and known paired changes.

Review tests verify disabled/authenticated modes, independent client/file persistence, source isolation, stale-write conflicts, and required owner/action validation. Server mode requires an operator-provided token and an absolute database path; durable hosting remains an operator responsibility.

## Browser checks

`python scripts/browser_smoke.py --url http://127.0.0.1:8002` passed against the built application:

- High-priority/log/seven-day/predictive defaults and expected outcomes for all three demos.
- Model switching, daily/weekly controls, delay-pattern scope and context display.
- Review validation, save and reload persistence.
- Open→overdue→arrival transitions, reload persistence, and exclusion of open calls from completed denominators.
- Duplicate-ID protection and corrupted-storage preservation/explicit recovery.
- CSV export retaining shift/traffic/units columns, invalid-upload errors, and a 390px mobile layout.
- No browser page errors.

The script requires Playwright 1.62.0 and Chromium. `--browser auto` selects the installed Playwright browser; `--browser /usr/bin/chromium` selects a system browser. CI installs browser tools, waits for a healthy locally started API, and runs the same workflow. [GitHub CI](https://github.com/aaronk467/team-reliability/actions/runs/38975394899) completed successfully in 56 seconds, including pinned installs, the 56-test suite, exact dataset regeneration, frontend build and Chromium workflow.

## Benchmark

The [benchmark](../benchmarks/README.md) uses 200 runs per main scenario and 100 per prespecified sensitivity case. A second execution reproduced the checked-in JSON byte-for-byte. Independent probability checks run before simulation. Comparisons include predictive/plugin methods, raw/log I-MR, daily/weekly aggregation, low/high/variable volumes, short baselines and correlated calls.

Under the primary independent-call generator, predictive weekly limits signaled in 2/200 unchanged runs, detected 195/200 slowdowns and 141/200 improvements. Plug-in results were 5/200, 200/200 and 168/200. The uncertainty-aware method trades sensitivity for wider predictive bounds. Under serial dependence, unchanged-run alerts were 13/100 predictive and 21/100 plug-in: neither method automatically corrects correlation. Intervals, detection delays, design and source hash are in results.json; these are not field-performance or clinical guarantees.

## Public deployment status

Render reports commit `de729ae` Live. Public OpenAPI reports version 0.3.0. All three datasets exactly match the local CSVs; six public analyses (three scenarios × predictive/plugin models) match the complete local library responses. The field-like CSVs contain 845 high-priority calls per scenario. Public shared review config reports browser-local mode, accurately reflecting that persistent server storage is not configured.

The complete browser workflow listed above also passed against `https://responsewatch-lpj2.onrender.com`, including the new predictive controls, delay context, review validation/persistence, optional-column export and all three expected demo outcomes. No browser page errors occurred. This environment used the script's `--ca-forward` option to forward browser requests through Python's trusted system CA store; HTTPS certificate verification remained enabled.

Browser-local open/completed records and local reviews are isolated to the user's browser/source. Optional server reviews do not make the dispatch register shared or establish durable storage on a free ephemeral host.

The version 0.3 Docker image built successfully with TLS verification retained. A running container reported version 0.3.0 and returned an 845-call high-priority predictive analysis exactly equal to the local library, with full typed metadata and the expected disabled optional shared mode.
