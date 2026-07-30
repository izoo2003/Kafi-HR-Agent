"""Job description & scoring criteria schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class JobDescriptionCreate(BaseModel):
    title: str = Field(min_length=1)
    department_id: int
    description_text: str = Field(min_length=1)
    requirements_text: str | None = None
    status: Literal["draft", "open", "closed"] = "draft"


class JobDescriptionUpdate(BaseModel):
    title: str | None = None
    department_id: int | None = None
    description_text: str | None = None
    requirements_text: str | None = None
    status: Literal["draft", "open", "closed"] | None = None
    file_path: str | None = None


class JobDescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department_id: int
    description_text: str
    requirements_text: str | None
    file_path: str | None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime


class ScoringCriteriaCreate(BaseModel):
    criterion_name: str = Field(min_length=1)
    # Proficiency level 1–10 (1 = very low, 10 = expert). Scorer normalizes across skills.
    weight: float = Field(ge=1, le=10)
    scoring_rules: dict[str, Any]


class ScoringCriteriaUpdate(BaseModel):
    criterion_name: str | None = None
    weight: float | None = Field(default=None, ge=1, le=10)
    scoring_rules: dict[str, Any] | None = None


class ScoringCriteriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_description_id: int
    criterion_name: str
    weight: float
    scoring_rules: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class ScoringCriteriaReplace(BaseModel):
    """Replace all skills for a job. Each weight is a proficiency level 1–10 (1=very low, 10=expert)."""

    criteria: list[ScoringCriteriaCreate]
