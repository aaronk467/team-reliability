# Validation record

Validated in the cloud workspace on 2026-10-16 with Python 3.12.14, Node 24.19.0, npm 11.9.0, and system Chromium.

- `./scripts/install.sh`: completed dependency installation, Vite production build, and 24 passing Python statistics/API tests.
- Known-answer tests cover I-MR limits, moving range constants, Wilson confidence limits, nonclipped variable-denominator p-chart limits, frozen baselines, and a planted signal. Additional cases exercise sparse/constant baselines, unstable-baseline warnings, priority filtering, timestamp validation, and API errors.
- Running HTTP API: each of three synthetic datasets analyzed successfully with 720 high-priority calls and four zones.
- Production frontend served by FastAPI: loaded with no browser page errors and three actual charts. Browser checks exercised priority filtering, dataset switching, dispatch-log and methods tabs, completed-call validation and logging, reload persistence, CSV import and download, and a 390px mobile viewport without page overflow.
- Screenshot in this directory uses only synthetic demonstration data.

## Public deployment checks

Live service: [ResponseWatch](https://responsewatch-lpj2.onrender.com) · [API documentation](https://responsewatch-lpj2.onrender.com/docs). Render’s deployment screenshot reports Live at commit `16d90d6`.

Live HTTPS requests returned HTTP 200 for `/api/health`, `/api/datasets`, `/docs`, and `/openapi.json`. All three demonstration datasets were retrieved and successfully analyzed with `priority="high"`, `baseline_days=20`, and `target_minutes=8`. Each response contained 720 completed calls and four zones, matched the local analysis exactly, and had finite numeric outputs.

| Dataset | High-priority completed calls | Late calls |
| --- | ---: | ---: |
| `stable` | 720 | 271 |
| `south_shift` | 720 | 325 |
| `improvement` | 720 | 151 |

Public browser verification also passed: the dashboard returned HTTP 200 and rendered three charts; priority filtering and analyses for all three datasets worked, with zero page or HTTP errors. The broader interaction checks listed above, including CSV import and mobile layout, were performed locally.

For public browser verification, Chromium’s separate trust store lacked the cloud proxy CA. Browser requests were forwarded through a Python HTTPS client using the installed `/etc/ssl/certs/ca-certificates.crt` trust bundle. TLS verification remained enabled, and the browser used real live responses, with no mocked data. GitHub CI execution is separate from these checks. Browser-local logging is a demonstration; the application is stateless and does not include a production dispatch database or authentication.

The Docker image built successfully with the cloud's trusted CA bundle supplied as an optional BuildKit secret and proxy DNS configured for the build. The running container served the production dashboard, returned a healthy API response, and successfully analyzed 720 high-priority calls from the South-shift dataset. TLS verification remained enabled.

## Version 0.2 local validation

The updated install script completed dependency installation, production build, and all 24 tests. Independent known cases cover log-transformed I-MR, finite-sum binomial quantiles and tail decisions, a 100,000-call bin, zero-duration handling, before/after summaries, and bins that cannot cross the frozen baseline boundary. API validation rejects invalid chart settings and boolean numeric inputs.

`python scripts/browser_smoke.py --url http://127.0.0.1:8002` passed against the running production build. It checked high/log/seven-day defaults, exact expected outcomes in all three demos, daily-versus-weekly settings, open→overdue→arrival transitions, reload persistence, exclusion of open calls from completed denominators, duplicate-ID rejection, corrupt-storage preservation and explicit recovery, CSV export and invalid-upload errors, and a 390px mobile layout. No browser page errors occurred. The browser test requires Playwright and Chromium; use `--browser` to select an installed Chromium binary.

The [seeded benchmark](../benchmarks/README.md) was run with 200 independent replicates per scenario, reproduced byte-for-byte, and reports chance-signal rates, detection probability with Monte Carlo intervals, and conditional detection delay. The default weekly chart detected 200/200 simulated slowdowns and 168/200 improvements; unchanged processes signaled in 5/200 runs. These are results for the documented simulation, not field-performance guarantees.

Version **0.2.0**, deployed from source commit `608f0a8`, passed public verification. Health, API docs, and OpenAPI returned HTTP 200; OpenAPI reported `0.2.0`. Each public dataset exactly matched its local CSV, and all three high-priority analyses using the new defaults matched the entire local analysis response with finite numbers. South monitoring late rates and exact-binomial signals were stable 46%/0, deterioration 100%/4, and improvement 6%/3.

`python scripts/browser_smoke.py --url https://responsewatch-lpj2.onrender.com --ca-forward` passed the same complete workflow listed above, including the open-call lifecycle, reload persistence, duplicate-ID rejection, corrupted-storage preservation/recovery, and mobile layout. No page errors occurred. The CA forwarding method used real HTTPS responses with the installed trust bundle and kept TLS verification enabled, as described above.

The version 0.2 Docker image built successfully. Its running API reported version `0.2.0`, used the new log/seven-day defaults, and returned the expected four South deterioration signals. Package installation retained TLS verification with the optional cloud CA build secret.
