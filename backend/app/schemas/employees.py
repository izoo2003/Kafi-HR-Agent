"""Department & Employee Pydantic schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Numeric(12, 2) → at most 10 digits before the decimal (max 9_999_999_999.99)
_MAX_BASE_SALARY = Decimal("9999999999.99")

DOCUMENT_CATEGORIES = frozenset(
    {"cnic", "cnic_front", "cnic_back", "education", "other", "photo", "client"}
)
CNIC_IMAGE_CATEGORIES = frozenset({"cnic_front", "cnic_back", "cnic"})
IMAGE_ONLY_DOCUMENT_CATEGORIES = CNIC_IMAGE_CATEGORIES | frozenset({"photo"})


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


class EmployeeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    category: str
    title: str | None
    original_filename: str
    mime_type: str | None
    created_at: datetime
    updated_at: datetime


class EmployeeReferenceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference_id: int
    original_filename: str
    mime_type: str | None
    created_at: datetime
    updated_at: datetime


class EmployeeReferenceCreate(BaseModel):
    full_name: str = Field(min_length=1)
    relation: str = Field(min_length=1, max_length=120)
    phone: str | None = None
    cnic: str | None = None
    notes: str | None = None


class EmployeeReferenceUpdate(BaseModel):
    full_name: str | None = None
    relation: str | None = None
    phone: str | None = None
    cnic: str | None = None
    notes: str | None = None


class EmployeeReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    full_name: str
    relation: str
    phone: str | None
    cnic: str | None
    notes: str | None
    documents: list[EmployeeReferenceDocumentRead] = []
    created_at: datetime
    updated_at: datetime


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1)
    department_id: int
    role_title: str | None = None
    job_description_text: str | None = None
    employment_type: str | None = "full_time"
    date_joined: date | None = None
    base_salary: Decimal | None = None
    manager_id: int | None = None
    user_id: int | None = None
    status: str = "active"

    cnic: str | None = None
    email: str | None = None
    personal_mobile: str | None = None
    alternate_mobile: str | None = None
    father_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    marital_status: str | None = None
    current_address: str | None = None
    permanent_address: str | None = None
    city: str | None = None
    nationality: str | None = None

    bank_name: str | None = None
    account_title: str | None = None
    account_number: str | None = None
    iban: str | None = None
    branch_name: str | None = None
    branch_code: str | None = None

    @field_validator("base_salary")
    @classmethod
    def salary_in_range(cls, v: Decimal | None) -> Decimal | None:
        return _validate_salary(v)


class EmployeeUpdate(BaseModel):
    employee_code: str | None = Field(default=None, min_length=1, max_length=64)
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

    cnic: str | None = None
    email: str | None = None
    personal_mobile: str | None = None
    alternate_mobile: str | None = None
    father_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    marital_status: str | None = None
    current_address: str | None = None
    permanent_address: str | None = None
    city: str | None = None
    nationality: str | None = None

    bank_name: str | None = None
    account_title: str | None = None
    account_number: str | None = None
    iban: str | None = None
    branch_name: str | None = None
    branch_code: str | None = None

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

    cnic: str | None = None
    email: str | None = None
    personal_mobile: str | None = None
    alternate_mobile: str | None = None
    father_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    marital_status: str | None = None
    current_address: str | None = None
    permanent_address: str | None = None
    city: str | None = None
    nationality: str | None = None

    bank_name: str | None = None
    account_title: str | None = None
    account_number: str | None = None
    iban: str | None = None
    branch_name: str | None = None
    branch_code: str | None = None

    created_at: datetime
    updated_at: datetime


class EmployeeDetailRead(EmployeeRead):
    documents: list[EmployeeDocumentRead] = []
    references: list[EmployeeReferenceRead] = []
