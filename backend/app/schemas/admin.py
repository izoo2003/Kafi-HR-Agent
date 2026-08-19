"""Admin panel schemas — FEATURE_ADMIN_PANEL.md."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

class AttendanceTodaySnapshot(BaseModel):
    present: int = 0
    absent: int = 0
    late: int = 0
    on_leave: int = 0
    half_day: int = 0
    holiday: int = 0
    total_marked: int = 0


class AdminDashboardRead(BaseModel):
    agent_status: Literal["ok", "degraded", "down"] = "ok"
    agent_mode: Literal["standalone", "registered"] = "standalone"
    registered_employees_active: int = Field(
        description="Self-registered employee accounts (username + PIN signup only).",
    )
    staff_users_active: int = Field(
        description="Staff/system accounts (HR admin, auditor, payroll, etc.) — not self-service signups.",
    )
    hr_employee_records_active: int = Field(
        description="Active employee records maintained by HR (roster), excluding self-registered codes.",
    )
    departments: int = 0
    open_job_descriptions: int = 0
    candidates_pending_review: int = 0
    attendance_today: AttendanceTodaySnapshot = Field(default_factory=AttendanceTodaySnapshot)
    leave_requests_pending: int = 0
    payroll_runs_pending_approval: int = 0
