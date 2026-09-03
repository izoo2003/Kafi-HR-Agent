"""Payroll models — DATABASE_SCHEMA.md §5."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
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


class PayrollSheetAdjustment(Base, TimestampMixin):
    """Per-employee monthly extras on the salary sheet (allowance, bonus, loan, advance, mode, remarks)."""

    __tablename__ = "payroll_sheet_adjustments"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "period_month",
            "period_year",
            name="uq_payroll_sheet_employee_period",
        ),
    )

    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False, index=True)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    allowance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    loan_deduction_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    advance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    payment_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    days_present: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_absent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_late: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_half_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leave_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overtime_bonus_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_tax_override: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)


class TaxYear(Base, TimestampMixin):
    """Named tax year (e.g. 2026-27) with editable progressive slabs."""

    __tablename__ = "tax_years"

    label: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TaxSlab(Base, TimestampMixin):
    __tablename__ = "tax_slabs"

    tax_year_id: Mapped[int] = mapped_column(ForeignKey("tax_years.id"), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Annual taxable income band (PKR). max_amount NULL = no upper cap.
    min_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    max_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    fixed_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    # Taxable excess is measured above this threshold (usually = min_amount for band start).
    excess_over: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
