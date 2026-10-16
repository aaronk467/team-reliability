"""HTTP delivery of ResponseWatch's independently usable statistical library."""
from pathlib import Path
import csv

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .schemas import (
    AnalysisResponse,
    AnalyzeRequest,
    DatasetInfo,
    DatasetResponse,
    DispatchRecord,
    HealthResponse,
    ValidatedRecord,
)
from .stats import analyze, validate_records
from .reviews import router as reviews_router

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(
    title="ResponseWatch",
    version="0.3.0",
    description=(
        "Frozen-baseline ambulance response monitoring. All analysis dates are UTC. "
        "Beta-binomial predictive limits include baseline-rate estimation uncertainty. "
        "Signals and recorded delay associations prompt investigation, not causal attribution."
    ),
)


@app.get('/api/health', response_model=HealthResponse)
def health():
    """Read-only service health check."""
    return {"status": "ok"}


@app.get('/api/datasets', response_model=list[DatasetInfo])
def datasets():
    """List the three reproducible synthetic demonstration datasets."""
    return [{"name": p.stem, "filename": p.name} for p in sorted((ROOT / 'datasets').glob('*.csv'))]


@app.get('/api/datasets/{name}', response_model=DatasetResponse, response_model_exclude_unset=True)
def dataset(name: str):
    """Return CSV records with optional context retained and original timestamp strings."""
    options = {p.stem: p for p in (ROOT / 'datasets').glob('*.csv')}
    if name not in options:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    with options[name].open(newline='') as file:
        return {"name": name, "records": list(csv.DictReader(file))}


@app.post('/api/analyze', response_model=AnalysisResponse)
def analyze_endpoint(request: AnalyzeRequest):
    """Analyze completed records; the baseline is frozen before monitoring begins.

    Empty priority selections, duplicate identifiers, invalid timestamps, and
    invalid optional context produce HTTP 422 without calculating an analysis.
    Limits/changes and recorded context are descriptive; this is not a patient
    outcome model or an automated emergency alerting service.
    """
    try:
        return analyze(**request.model_dump(exclude_none=True))
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post('/api/validate-record', response_model=ValidatedRecord, response_model_exclude_unset=True)
def validate_record(record: DispatchRecord):
    """Normalize one completed record and return its calculated duration in minutes."""
    try:
        clean = validate_records([record.model_dump(exclude_none=True)])[0]
        clean.pop('_dt')
        return clean
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


app.include_router(reviews_router)

if (ROOT / 'frontend' / 'dist').is_dir():
    app.mount('/', StaticFiles(directory=ROOT / 'frontend' / 'dist', html=True), name='frontend')
