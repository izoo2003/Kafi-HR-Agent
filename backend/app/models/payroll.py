"""Payroll models — DATABASE_SCHEMA.md §5."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class PayrollStructure(Base, TimestampMixin):
    __tablename__ = "payroll_structures"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    overtime_rate_per_hour: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class PayrollRun(Base, TimestampMixin):
    __tablename__ = "payroll_runs"

    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Payslip(Base, TimestampMixin):
    __tablename__ = "payslips"

    payroll_run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    overtime_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    deductions_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    advances_deducted: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    generated_pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class Deduction(Base, TimestampMixin):
    __tablename__ = "deductions"

    payslip_id: Mapped[int] = mapped_column(ForeignKey("payslips.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalaryAdvance(Base, TimestampMixin):
    __tablename__ = "salary_advances"

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date_requested: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    amount_recovered: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
