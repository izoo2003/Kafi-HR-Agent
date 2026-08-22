"""KPI models — DATABASE_SCHEMA.md §6."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class KpiDefinition(Base, TimestampMixin):
    __tablename__ = "kpi_definitions"

    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False, index=True)
    owner_employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurement_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_period: Mapped[str | None] = mapped_column(String, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class KpiEntry(Base, TimestampMixin):
    __tablename__ = "kpi_entries"
    __table_args__ = (
        UniqueConstraint(
            "kpi_definition_id",
            "employee_id",
            "period_start",
            "period_end",
            name="uq_kpi_entry_period",
        ),
    )

    kpi_definition_id: Mapped[int] = mapped_column(
        ForeignKey("kpi_definitions.id"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    actual_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmployeeMonthlyPerformance(Base, TimestampMixin):
    """Finalized monthly performance score (/10) + optional AI summary."""

    __tablename__ = "employee_monthly_performance"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "period_year",
            "period_month",
            name="uq_employee_monthly_performance",
        ),
    )

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    score_out_of_10: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    overall_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    entries_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmployeeTrainingAssignment(Base, TimestampMixin):
    """AI-recommended course assigned to an employee (Things To Learn)."""

    __tablename__ = "employee_training_assignments"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)  # intermediate | advanced
    description: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True)
    url_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    department_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="assigned", nullable=False, index=True)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmployeeResignationNotice(Base, TimestampMixin):
    """HR-issued resignation letter awaiting employee acceptance."""

    __tablename__ = "employee_resignation_notices"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    letter_body: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    issued_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
