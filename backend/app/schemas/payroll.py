"""Payroll schemas — salaries list for active employees (Phase 4 scaffold)."""
from __future__ import annotations

from datetime import datetime
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
