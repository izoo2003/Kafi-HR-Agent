"""CV screening / candidate schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CandidateCreateMeta(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None


class CandidateUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    parsed_data: dict[str, Any] | None = None
    status: Literal["uploaded", "parsed", "scored", "shortlisted", "rejected", "hired"] | None = None


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_description_id: int
    full_name: str | None
    email: str | None
    phone: str | None
    cv_file_path: str
    parsed_data: dict[str, Any] | None
    status: str
    created_at: datetime
    updated_at: datetime


class CandidateScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    scoring_criteria_id: int
    raw_score: float | None
    notes: str | None


class CandidateRankingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_description_id: int
    candidate_id: int
    total_score: float
    rank_position: int
    computed_at: datetime


class RankingRow(BaseModel):
    candidate_id: int
    full_name: str | None
    email: str | None
    status: str
    total_score: float
    rank_position: int
    pending_manual_review: bool = False


class ScoreOverrideRequest(BaseModel):
    scoring_criteria_id: int
    raw_score: float
    reason: str = Field(min_length=3)


class SkillEvaluationRow(BaseModel):
    skill: str
    required_level: float
    matched: bool
    raw_score: float | None
    max_points: float
    notes: str | None


class CandidateEvaluation(BaseModel):
    candidate_id: int
    job_description_id: int
    job_title: str
    overall_score: float | None
    rank_position: int | None
    recommendation: Literal["shortlist", "consider", "reject"]
    recommendation_label: str
    summary: str
    strengths: list[str]
    gaps: list[str]
    skills: list[SkillEvaluationRow]


class HireRequest(BaseModel):
    employee_code: str
    department_id: int
    role_title: str | None = None
    base_salary: float | None = None
    date_joined: str | None = None  # ISO date
