"""Department & Employee Pydantic schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Numeric(12, 2) → at most 10 digits before the decimal (max 9_999_999_999.99)
_MAX_BASE_SALARY = Decimal("9999999999.99")


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    head_employee_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    head_employee_id: int | None = None


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    head_employee_id: int | None
    created_at: datetime
    updated_at: datetime


def _validate_salary(value: Decimal | None) -> Decimal | None:
    if value is None:
        return value
    if value < 0:
        raise ValueError("base_salary cannot be negative")
    if value > _MAX_BASE_SALARY:
        raise ValueError(
            f"base_salary too large (max {_MAX_BASE_SALARY}). "
            "Use a realistic salary — e.g. 150000, not 12+ digit test values."
        )
    return value


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1)
    department_id: int
    role_title: str = Field(min_length=1)
    job_description_text: str | None = None
    employment_type: str | None = "full_time"
    date_joined: date | None = None
    base_salary: Decimal | None = None
    manager_id: int | None = None
    user_id: int | None = None
    status: str = "active"

    @field_validator("base_salary")
    @classmethod
    def salary_in_range(cls, v: Decimal | None) -> Decimal | None:
        return _validate_salary(v)


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    department_id: int | None = None
    role_title: str | None = None
    job_description_text: str | None = None
    employment_type: str | None = None
    date_joined: date | None = None
    base_salary: Decimal | None = None
    manager_id: int | None = None
    user_id: int | None = None
    status: str | None = None

    @field_validator("base_salary")
    @classmethod
    def salary_in_range(cls, v: Decimal | None) -> Decimal | None:
        return _validate_salary(v)


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    employee_code: str
    full_name: str
    department_id: int
    role_title: str
    job_description_text: str | None = None
    employment_type: str | None
    date_joined: date | None
    date_exited: date | None
    status: str
    base_salary: Decimal | None
    manager_id: int | None
    created_at: datetime
    updated_at: datetime
