"""Optional token-protected SQLite review register with optimistic concurrency.

The operator must place RESPONSEWATCH_DB_PATH on persistent storage to retain
records across hosting replacement. No storage durability is inferred here.
"""
from datetime import date, datetime, timezone
from contextlib import contextmanager
import hmac
import os
from pathlib import Path
import sqlite3
from typing import Literal
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

router=APIRouter(prefix='/api/reviews', tags=['Resolution reviews'])


class ReviewInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source: str=Field(min_length=1,max_length=160)
    zone: str=Field(min_length=1,max_length=120)
    owner: str=Field(default='',max_length=120,description='Reviewer alias; no personal or patient information.')
    status: Literal['open','in_progress','resolved']='open'
    action: str=Field(default='',max_length=4000)
    due_date: date | None=None
    version: StrictInt=Field(default=0,ge=0,description='Last version read, or zero for a new review. Stale writes return409.')

    @field_validator('source','zone','owner','action')
    @classmethod
    def trim_text(cls,value):
        return value.strip()

    @model_validator(mode='after')
    def require_review_details(self):
        if not self.source or not self.zone:
            raise ValueError('source and zone cannot be blank')
        if self.status!='open' and not self.owner:
            raise ValueError('Assign a reviewer alias before progressing a review')
        if self.status=='resolved' and not self.action:
            raise ValueError('Document the action before resolving a review')
        return self


class Review(ReviewInput):
    updated_at: str


class ReviewConfig(BaseModel):
    shared_enabled: bool
    storage: Literal['operator_configured_sqlite','browser_local']
    message: str


def settings():
    token=os.environ.get('RESPONSEWATCH_REVIEW_TOKEN','')
    path=os.environ.get('RESPONSEWATCH_DB_PATH','')
    return token,path


@router.get('/config',response_model=ReviewConfig)
def review_config():
    token,path=settings()
    enabled=len(token)>=32 and bool(path) and Path(path).is_absolute()
    return dict(shared_enabled=enabled,storage='operator_configured_sqlite' if enabled else 'browser_local',
                message=('Shared token-protected reviews are enabled. Durability depends on the operator placing the database on persistent storage; configured path alone does not prove persistence.' if enabled else
                         'Browser-local review mode. Shared reviews require a server token of at least32 characters and RESPONSEWATCH_DB_PATH on operator-provided persistent storage. Free Render instance files are ephemeral.'))


def authorize(authorization):
    token,path=settings()
    if len(token)<32 or not path or not Path(path).is_absolute():
        raise HTTPException(503,'Shared reviews are not configured; use browser-local review mode.')
    scheme,_,credential=(authorization or '').partition(' ')
    if scheme.lower()!='bearer' or not hmac.compare_digest(credential.encode(),token.encode()):
        raise HTTPException(401,'A valid shared review token is required.',headers={'WWW-Authenticate':'Bearer'})
    return path


@contextmanager
def connect(path):
    try:
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(path,timeout=5)
        db.row_factory=sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS reviews (source TEXT NOT NULL,zone TEXT NOT NULL,owner TEXT NOT NULL,status TEXT NOT NULL,action TEXT NOT NULL,due_date TEXT,version INTEGER NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(source,zone))')
    except (OSError,sqlite3.Error) as exc:
        raise HTTPException(503,'Review storage is unavailable; existing data were not replaced.') from exc
    try:
        with db:
            yield db
    finally:
        db.close()


@router.get('',response_model=list[Review])
def list_reviews(source: str=Query(min_length=1,max_length=160),authorization: str | None=Header(default=None)):
    path=authorize(authorization)
    try:
        with connect(path) as db:
            return [dict(row) for row in db.execute('SELECT * FROM reviews WHERE source=? ORDER BY zone',(source.strip(),))]
    except sqlite3.Error as exc:
        raise HTTPException(503,'Review storage could not be read.') from exc


@router.put('',response_model=Review)
def save_review(review: ReviewInput,authorization: str | None=Header(default=None)):
    path=authorize(authorization)
    try:
        with connect(path) as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT version FROM reviews WHERE source=? AND zone=?',(review.source,review.zone)).fetchone()
            actual=previous['version'] if previous else 0
            if review.version!=actual:
                raise HTTPException(409,'This review changed elsewhere. Reload it before saving.')
            result=review.model_dump(mode='json')
            result.update(version=actual+1,updated_at=datetime.now(timezone.utc).isoformat())
            db.execute('INSERT INTO reviews VALUES (:source,:zone,:owner,:status,:action,:due_date,:version,:updated_at) ON CONFLICT(source,zone) DO UPDATE SET owner=excluded.owner,status=excluded.status,action=excluded.action,due_date=excluded.due_date,version=excluded.version,updated_at=excluded.updated_at',result)
            return result
    except sqlite3.Error as exc:
        raise HTTPException(503,'Review storage could not be updated; retry after reloading.') from exc
