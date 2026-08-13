"""Payroll schemas — salaries, tax years/slabs, attendance-based computation."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MAX_BASE_SALARY = Decimal("9999999999.99")


class PayrollSalaryRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    employee_code: str
    full_name: str
    department_id: int
    department_name: str | None = None
    role_title: str
    status: str
    base_salary: Decimal | None
    updated_at: datetime


class PayrollSalaryUpdate(BaseModel):
    base_salary: Decimal | None = Field(default=None)

    @field_validator("base_salary")
    @classmethod
    def salary_in_range(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        if v < 0:
            raise ValueError("base_salary cannot be negative")
        if v > _MAX_BASE_SALARY:
            raise ValueError(f"base_salary too large (max {_MAX_BASE_SALARY})")
        return v


# --- Tax years / slabs -------------------------------------------------------


class TaxSlabCreate(BaseModel):
    sort_order: int = 0
    min_amount: Decimal = Field(ge=0)
    max_amount: Decimal | None = None
    fixed_amount: Decimal = Field(default=Decimal("0"), ge=0)
    rate_percent: Decimal = Field(default=Decimal("0"), ge=0)
    excess_over: Decimal = Field(default=Decimal("0"), ge=0)


class TaxSlabRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tax_year_id: int
    sort_order: int
    min_amount: Decimal
    max_amount: Decimal | None
    fixed_amount: Decimal
    rate_percent: Decimal
    excess_over: Decimal
    created_at: datetime
    updated_at: datetime


class TaxYearCreate(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    start_date: date
    end_date: date
    is_active: bool = True
    notes: str | None = None
    slabs: list[TaxSlabCreate] = []


class TaxYearUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=32)
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class TaxYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    start_date: date
    end_date: date
    is_active: bool
    notes: str | None
    slabs: list[TaxSlabRead] = []
    created_at: datetime
    updated_at: datetime


class TaxSlabsReplace(BaseModel):
    slabs: list[TaxSlabCreate]


# --- Attendance-based salary computation -------------------------------------


class PayrollComputeRow(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    base_salary: Decimal
    per_day_rate: Decimal
    days_absent: int
    days_late: int
    days_half_day: int
    late_off_days: int
    leave_allowance: int
    leave_used: int
    absents_after_leave: int
    overtime_bonus_days: int
    attendance_deduction: Decimal
    overtime_amount: Decimal
    gross_after_attendance: Decimal
    annual_taxable_income: Decimal
    annual_tax: Decimal
    monthly_tax: Decimal
    net_salary: Decimal
    late_events: list[dict] = []
    notes: str | None = None


class PayrollComputeResult(BaseModel):
    period_month: int
    period_year: int
    period_start: date
    period_end: date
    tax_year_id: int
    tax_year_label: str
    month_days: int = 30
    employees: list[PayrollComputeRow]
