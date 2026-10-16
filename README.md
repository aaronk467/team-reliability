# ResponseWatch

[Open the live app](https://responsewatch-lpj2.onrender.com) · [Live API documentation](https://responsewatch-lpj2.onrender.com/docs)

ResponseWatch helps ambulance dispatch supervisors identify zones with unusually variable dispatch-to-arrival times and frequent missed response targets. A React/Vite dashboard presents a Python statistical library and FastAPI REST API. The focus is transparent statistical process control, with three reproducible synthetic dispatch logs for demonstration.

Select a dataset, priority, response-time target, and baseline length. Review zone summaries, the empirical 90th percentile, late-call risk with Wilson 95% intervals, individuals/moving-range charts, and daily late-fraction charts. Compare the stable scenario with the planted South deterioration and subsequent-period improvement scenarios. Signals identify where to investigate; they do not establish why a delay occurred or predict patient outcomes. The eight-minute default is illustrative and must be replaced with locally agreed policy.

![ResponseWatch dashboard using the synthetic South-shift scenario](docs/dashboard.png)

## Run locally

Use Python 3.11+ and Node.js 22.12+. From the repository root:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
pytest
uvicorn responsewatch.api:app --host 0.0.0.0 --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev -- --host 0.0.0.0
```

Open the Vite URL printed by the frontend command. The development frontend proxies API requests to port 8000. API documentation is available at `http://localhost:8000/docs`. For a production frontend build run `npm run build` inside `frontend`, then start or restart Uvicorn: the static frontend is mounted when the server starts.

## API and library

`GET /api/datasets` lists bundled demonstrations; `GET /api/datasets/{name}` retrieves one. `POST /api/analyze` accepts completed dispatch records and settings:

```json
{
  "records": [
    {"id":"demo-1","zone":"North","priority":"high","dispatched_at":"2026-01-01T12:00:00Z","arrived_at":"2026-01-01T12:07:00Z","delay_reason":""}
  ],
  "target_minutes": 8,
  "baseline_days": 20,
  "priority": "high"
}
```

This example illustrates the record format; useful control charts require multiple baseline observations. Use the bundled datasets for a complete demonstration. The interactive `/docs` page documents request schemas and lets you try the endpoints. [API reference](docs/API.md) describes response fields. The installable Python package is `responsewatch`:

```python
import csv
from responsewatch.stats import analyze, validate_records

with open("datasets/south_shift.csv", newline="") as handle:
    records = list(csv.DictReader(handle))
report = analyze(records, target_minutes=8, baseline_days=20, priority="high")
print(report["summary"])
```

`analyze(records, target_minutes=8.0, baseline_days=20, priority="all")` returns overall and per-zone risk summaries, baseline dates, I-MR points and limits, daily p-chart points and limits, and warnings. `target_minutes` must be finite and positive; `baseline_days` is an integer from 1 to 3650; `priority` is an exact priority label or `all`. `validate_records(records)` validates a nonempty list of up to 100,000 record dictionaries and returns normalized copies sorted by dispatch time and ID. Invalid inputs raise `ValueError`. See [the statistical source](backend/responsewatch/stats.py) and [methods](docs/methods.md) for implementation, assumptions, and interpretation. Validation includes independently known statistical answers before presentation checks.

## Demonstrations and collection

- [Dataset README](datasets/README.md): scenario design, generation, and reproducibility.
- [Codebook](datasets/CODEBOOK.md): each field, units, allowed values, and derived measures.
- [Collection protocol](docs/collection.md): field workflow, clocks, privacy, missingness, and denominator handling.
- [Statistical methods](docs/methods.md): control limits, uncertainty, and limitations.
- [Deployment](docs/deployment.md): container workflow and public publication checklist.

All sample data are synthetic and contain no patient information. Upload only appropriately governed, deidentified operational logs. The current completed-call analysis does not include unresolved calls in its denominator; supervisors must separately report open and excluded records to avoid misleading real-time conclusions. This is a statistical review tool, not an emergency dispatch or clinical decision system.

Regenerate the exact demonstration files with `python datasets/generate.py`. Installation and builds use the committed dependency files.

## Public deployment

The app is deployed at [responsewatch-lpj2.onrender.com](https://responsewatch-lpj2.onrender.com). Render’s deployment screenshot reports **Live** at commit `16d90d6`. Local validation, live HTTPS API checks, and public browser checks passed. All three demonstration analyses matched local results exactly. See the [deployment and validation record](docs/deployment.md).

To recreate the deployment, use the committed Render Blueprint (`render.yaml`): [create a Render service](https://render.com/deploy?repo=https://github.com/aaronk467/team-reliability) with your connected GitHub account.

For cloud setup, `./scripts/install.sh` installs frozen frontend dependencies, pinned Python dependencies, builds the dashboard, and runs statistical/API tests. It uses a writable temporary npm cache.
