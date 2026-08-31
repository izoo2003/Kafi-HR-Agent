"""Employee Development — resignation letter schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ResignationStatus = Literal["draft", "pending", "accepted", "rejected", "cancelled"]
ResignationDirection = Literal["hr", "employee"]


class EmployeeResignationGenerateRequest(BaseModel):
    employee_id: int | None = Field(default=None, ge=1)
    reason: str | None = Field(default=None, max_length=2000)
    effective_date: date | None = None


class EmployeeResignationGenerateResponse(BaseModel):
    employee_id: int
    employee_name: str
    subject: str
    letter_body: str
    reason: str | None = None
    effective_date: date | None = None
    direction: ResignationDirection = "hr"


class EmployeeResignationCreateRequest(BaseModel):
    employee_id: int | None = Field(default=None, ge=1)
    subject: str = Field(min_length=3, max_length=300)
    letter_body: str = Field(min_length=20, max_length=20000)
    reason: str | None = Field(default=None, max_length=2000)
    effective_date: date | None = None
    submit: bool = False


class EmployeeResignationUpdateRequest(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=300)
    letter_body: str | None = Field(default=None, min_length=20, max_length=20000)
    reason: str | None = Field(default=None, max_length=2000)
    effective_date: date | None = None
    status: Literal["cancelled"] | None = None


class EmployeeResignationRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


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
    direction: ResignationDirection = "hr"
    issued_by: int
    issued_at: datetime
    accepted_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    reviewed_by: int | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeResignationListResponse(BaseModel):
    items: list[EmployeeResignationRead]
    total: int
