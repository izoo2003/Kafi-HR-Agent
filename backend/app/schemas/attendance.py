"""Attendance schemas — FEATURE_ATTENDANCE.md."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
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


class LateEvent(BaseModel):
    date: date
    check_in_time: str


class DayClassification(BaseModel):
    date: date
    day_type: str
    weekday: str


class PeriodEmployeeReport(BaseModel):
    employee_id: int | None = None
    employee_code: str | None = None
    full_name: str
    matched_employee: bool = False
    base_salary: Decimal | None = None
    tenure_months: int = 0
    leave_allowance: int = 0
    leave_used: int = 0
    days_present: int = 0
    days_late: int = 0
    days_half_day: int = 0
    days_absent: int = 0
    absents_after_leave: int = 0
    late_off_days: int = 0
    overtime_bonus_days: int = 0
    deduction_days: float = 0
    per_day_rate: float = 0
    estimated_deduction_amount: float = 0
    estimated_overtime_amount: float = 0
    estimated_net_salary: float = 0
    late_events: list[LateEvent] = []
    half_day_dates: list[date] = []
    absent_dates: list[date] = []
    overtime_dates: list[date] = []


class AttendancePeriodReport(BaseModel):
    period_start: date
    period_end: date
    month_days: int = 30
    majority_absent_threshold: float = 0.8
    late_after: str = "09:40"
    half_day_after: str = "11:30"
    lates_per_off: int = 3
    imported_rows: int = 0
    errors: list[ImportErrorRow] = []
    non_working_days: list[DayClassification] = []
    employees: list[PeriodEmployeeReport] = []
