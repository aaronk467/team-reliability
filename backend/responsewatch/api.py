"""HTTP delivery of ResponseWatch's independently usable statistical library."""
from pathlib import Path
import csv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from .stats import analyze, validate_records

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="ResponseWatch", version="0.1.0", description="Frozen-baseline response time monitoring; all dates UTC.")

class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[dict] = Field(min_length=1,max_length=100000)
    target_minutes: float = Field(default=8,gt=0,allow_inf_nan=False)
    baseline_days: StrictInt = Field(default=20,ge=1,le=3650)
    priority: StrictStr = "all"

@app.get('/api/health')
def health():
    return {"status":"ok"}

@app.get('/api/datasets')
def datasets():
    return [{"name":p.stem,"filename":p.name} for p in sorted((ROOT/'datasets').glob('*.csv'))]

@app.get('/api/datasets/{name}')
def dataset(name: str):
    options={p.stem:p for p in (ROOT/'datasets').glob('*.csv')}
    if name not in options:
        raise HTTPException(status_code=404,detail="Unknown dataset")
    with options[name].open(newline='') as file:
        return {"name":name,"records":list(csv.DictReader(file))}

@app.post('/api/analyze')
def analyze_endpoint(request: AnalyzeRequest):
    try:
        return analyze(**request.model_dump())
    except (ValueError,OverflowError) as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.post('/api/validate-record')
def validate_record(record: dict):
    try:
        clean=validate_records([record])[0]
        clean.pop('_dt')
        return clean
    except (ValueError,OverflowError) as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

if (ROOT/'frontend'/'dist').is_dir():
    app.mount('/', StaticFiles(directory=ROOT/'frontend'/'dist',html=True),name='frontend')
