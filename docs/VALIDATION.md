# Validation record

Validated in the cloud workspace on 2026-10-16 with Python 3.12.14, Node 24.19.0, npm 11.9.0, and system Chromium.

- `./scripts/install.sh`: completed dependency installation, Vite production build, and 14 passing Python statistics/API tests.
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
