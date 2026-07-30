"""Pydantic response/request shapes for the REST API. Kept separate from the
SQLAlchemy models (app/db/models.py) so the DB schema can evolve without
breaking the frontend contract, and vice versa.
"""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class PositionSummaryOut(BaseModel):
    position: str
    candidates_scored: int
    top_candidate: str | None
    top_score: float | None
    top_verdict: str | None


class CandidateRankingOut(BaseModel):
    rank: int | None
    application_id: int
    candidate_name: str
    email: str
    phone: str | None
    location: str | None
    position: str
    score: float | None
    verdict: str | None
    source: str
    status: str
    education_summary: str | None
    experience_summary: str | None
    key_strengths: list[str]
    hiring_summary: str | None
    submitted_at: dt.datetime
    scored_at: dt.datetime | None


class PipelineRunResult(BaseModel):
    new_applications: int
    scored: int
    failed: int
    reports: list[str] = []


class FetchResult(BaseModel):
    new_applications: int
    pending_unscored: int = 0
    message: str = ""


class ScoreResult(BaseModel):
    succeeded: int
    failed: int


class ErrorOut(BaseModel):
    detail: str
