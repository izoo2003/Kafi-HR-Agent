"""Attendance schemas — FEATURE_ATTENDANCE.md."""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AttendanceRuleCreate(BaseModel):
    name: str
    shift_start: time
    shift_end: time
    grace_period_minutes: int = 15
    half_day_threshold_minutes: int = 240
    applies_to_department_id: int | None = None


class AttendanceRuleUpdate(BaseModel):
    name: str | None = None
    shift_start: time | None = None
    shift_end: time | None = None
    grace_period_minutes: int | None = None
    half_day_threshold_minutes: int | None = None
    applies_to_department_id: int | None = None


class AttendanceRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    shift_start: time
    shift_end: time
    grace_period_minutes: int
    half_day_threshold_minutes: int
    applies_to_department_id: int | None
    created_at: datetime
    updated_at: datetime


class AttendanceRecordCreate(BaseModel):
    employee_id: int
    date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
    notes: str | None = None


class AttendanceRecordUpdate(BaseModel):
    check_in: datetime | None = None
    check_out: datetime | None = None
    notes: str | None = None
    reason: str = Field(min_length=3, description="Required for edits — audit trail")


class AttendanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    date: date
    check_in: datetime | None
    check_out: datetime | None
    source: str
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class LeaveRequestCreate(BaseModel):
    employee_id: int
    leave_type: Literal["annual", "sick", "unpaid", "other"] = "annual"
    start_date: date
    end_date: date
    reason: str | None = None


class LeaveRequestUpdate(BaseModel):
    status: Literal["approved", "rejected"]
    reason: str | None = None


class LeaveRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    status: str
    approved_by: int | None
    reason: str | None
    created_at: datetime
    updated_at: datetime


class AttendanceSummary(BaseModel):
    employee_id: int
    period_start: date
    period_end: date
    days_present: int
    days_late: int
    days_half_day: int
    days_absent: int
    days_on_leave: int
    total_working_days: int
    overtime_hours: float = 0.0


class ImportErrorRow(BaseModel):
    row: int
    message: str


class AttendanceImportResult(BaseModel):
    imported: int
    errors: list[ImportErrorRow]


class BiometricSyncResult(BaseModel):
    message: str
    punches_fetched: int = 0
