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


class PayrollSheetAdjustmentInput(BaseModel):
    employee_id: int
    allowance_amount: Decimal = Field(default=Decimal("0"), ge=0)
    bonus_amount: Decimal = Field(default=Decimal("0"), ge=0)
    loan_deduction_amount: Decimal = Field(default=Decimal("0"), ge=0)
    advance_amount: Decimal = Field(default=Decimal("0"), ge=0)
    payment_mode: str | None = Field(default=None, max_length=32)
    remarks: str | None = None
    base_salary: Decimal | None = Field(default=None)
    days_present: int | None = Field(default=None, ge=0)
    days_absent: int | None = Field(default=None, ge=0)
    days_late: int | None = Field(default=None, ge=0)
    days_half_day: int | None = Field(default=None, ge=0)
    overtime_bonus_days: int | None = Field(default=None, ge=0)
    monthly_tax_override: Decimal | None = Field(default=None, ge=0)

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


class PayrollSheetAdjustmentsSave(BaseModel):
    period_month: int = Field(ge=1, le=12)
    period_year: int = Field(ge=2000, le=2100)
    items: list[PayrollSheetAdjustmentInput]


class PayrollComputeRow(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    department_name: str | None = None
    role_title: str = ""
    base_salary: Decimal
    per_day_rate: Decimal
    days_present: int = 0
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
    late_deduction_amount: Decimal = Decimal("0")
    half_day_deduction: Decimal = Decimal("0")
    allowance_amount: Decimal = Decimal("0")
    bonus_amount: Decimal = Decimal("0")
    loan_deduction_amount: Decimal = Decimal("0")
    advance_amount: Decimal = Decimal("0")
    payment_mode: str | None = "IBFT"
    remarks: str | None = None
    gross_salary: Decimal = Decimal("0")
    gross_after_attendance: Decimal
    annual_taxable_income: Decimal
    annual_tax: Decimal
    monthly_tax: Decimal
    net_salary: Decimal
    net_payable: Decimal = Decimal("0")
    tax_manual: bool = False
    late_events: list[dict] = []
    notes: str | None = None


class PayrollTaxSlabLite(BaseModel):
    sort_order: int
    min_amount: Decimal
    max_amount: Decimal | None = None
    fixed_amount: Decimal
    rate_percent: Decimal
    excess_over: Decimal


class PayrollAiSummaryRead(BaseModel):
    period_month: int
    period_year: int
    employee_count: int
    total_net_payable: float
    payment_mode_counts: dict[str, int]
    summary_text: str
    generated_at: datetime | None = None


class PayrollComputeResult(BaseModel):
    period_month: int
    period_year: int
    period_start: date
    period_end: date
    tax_year_id: int
    tax_year_label: str
    month_days: int = 30
    lates_per_off: int = 3
    company_name: str = "KAFI COMMODITIES (PVT) LTD"
    tax_slabs: list[PayrollTaxSlabLite] = []
    employees: list[PayrollComputeRow]
    ai_summary: PayrollAiSummaryRead | None = None
