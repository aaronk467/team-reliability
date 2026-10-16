# Validation record

Validated in the cloud workspace on 2026-10-16 with Python 3.12.14, Node 24.19.0, npm 11.9.0, and system Chromium.

- `./scripts/install.sh`: completed dependency installation, Vite production build, and 14 passing Python statistics/API tests.
- Known-answer tests cover I-MR limits, moving range constants, Wilson confidence limits, nonclipped variable-denominator p-chart limits, frozen baselines, and a planted signal. Additional cases exercise sparse/constant baselines, unstable-baseline warnings, priority filtering, timestamp validation, and API errors.
- Running HTTP API: each of three synthetic datasets analyzed successfully with 720 high-priority calls and four zones.
- Production frontend served by FastAPI: loaded with no browser page errors and three actual charts. Browser checks exercised priority filtering, dataset switching, dispatch-log and methods tabs, completed-call validation and logging, reload persistence, CSV import and download, and a 390px mobile viewport without page overflow.
- Screenshot in this directory uses only synthetic demonstration data.

Public hosting and GitHub CI execution are separate from these local checks. A running public HTTPS service must still be verified after account-connected deployment. Browser-local logging is a demonstration; the application is stateless and does not include a production dispatch database or authentication.

The Docker image built successfully with the cloud's trusted CA bundle supplied as an optional BuildKit secret and proxy DNS configured for the build. The running container served the production dashboard, returned a healthy API response, and successfully analyzed 720 high-priority calls from the South-shift dataset. TLS verification remained enabled.
