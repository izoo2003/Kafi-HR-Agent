"""CV screening models — DATABASE_SCHEMA.md §3."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.base import TimestampMixin


class JobDescription(Base, TimestampMixin):
    __tablename__ = "job_descriptions"

    title: Mapped[str] = mapped_column(Text, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    description_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)


class ScoringCriteria(Base, TimestampMixin):
    __tablename__ = "scoring_criteria"

    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id"), nullable=False, index=True
    )
    criterion_name: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    scoring_rules: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id"), nullable=False, index=True
    )
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    cv_file_path: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="uploaded", nullable=False)


class CandidateScore(Base, TimestampMixin):
    __tablename__ = "candidate_scores"

    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    scoring_criteria_id: Mapped[int] = mapped_column(
        ForeignKey("scoring_criteria.id"), nullable=False
    )
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CandidateRanking(Base, TimestampMixin):
    __tablename__ = "candidate_rankings"

    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id"), nullable=False, index=True
    )
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
