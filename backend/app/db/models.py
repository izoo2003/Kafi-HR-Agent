"""SQLAlchemy models for CV ranking.

Candidate = a person (deduped by email).
Application = one submission by a candidate for one position, from one
source (gmail / google_form / whatsapp). Scoring results live on the
Application since the same person could apply to multiple roles.
"""
from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SourceChannel(str, enum.Enum):
    GMAIL = "gmail"
    GOOGLE_FORM = "google_form"
    WHATSAPP = "whatsapp"
    MANUAL = "manual"


class ApplicationStatus(str, enum.Enum):
    RECEIVED = "received"
    PARSED = "parsed"
    SCORED = "scored"
    FAILED = "failed"


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.UTC))

    applications: Mapped[list["Application"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "position_applied", "source", name="uq_candidate_position_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    candidate: Mapped["Candidate"] = relationship(back_populates="applications")

    position_applied: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[SourceChannel] = mapped_column(Enum(SourceChannel))
    source_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)  # gmail msg id / form row id

    cv_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cv_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.RECEIVED
    )

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rank_in_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    education_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    experience_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_strengths_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list[str]
    hiring_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    scored_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
