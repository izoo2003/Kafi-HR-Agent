"""Employee Development — resignation letter schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ResignationStatus = Literal["pending", "accepted", "cancelled"]


class EmployeeResignationGenerateRequest(BaseModel):
    employee_id: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)
    effective_date: date | None = None


class EmployeeResignationGenerateResponse(BaseModel):
    employee_id: int
    employee_name: str
    subject: str
    letter_body: str
    reason: str | None = None
    effective_date: date | None = None


class EmployeeResignationCreateRequest(BaseModel):
    employee_id: int = Field(ge=1)
    subject: str = Field(min_length=3, max_length=300)
    letter_body: str = Field(min_length=20, max_length=20000)
    reason: str | None = Field(default=None, max_length=2000)
    effective_date: date | None = None


class EmployeeResignationUpdateRequest(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=300)
    letter_body: str | None = Field(default=None, min_length=20, max_length=20000)
    reason: str | None = Field(default=None, max_length=2000)
    effective_date: date | None = None
    status: Literal["cancelled"] | None = None


class EmployeeResignationRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str | None = None
    employee_code: str | None = None
    subject: str
    letter_body: str
    reason: str | None = None
    effective_date: date | None = None
    status: ResignationStatus
    issued_by: int
    issued_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeResignationListResponse(BaseModel):
    items: list[EmployeeResignationRead]
    total: int
