"""KPI models — DATABASE_SCHEMA.md §6."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Float, ForeignKey, Numeric, String, Text, UniqueConstraint
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
