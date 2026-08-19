"""Admin control panel aggregation — FEATURE_ADMIN_PANEL.md §2.1."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.integration import interface as integration
from app.models.attendance import AttendanceRecord, LeaveRequest
from app.models.cv_screening import Candidate, JobDescription
from app.models.employees import Department, Employee
from app.models.identity import User
from app.models.payroll import PayrollRun
from app.models.system import IntegrationRegistry
from app.schemas.admin import AdminDashboardRead, AttendanceTodaySnapshot
from app.services.auth_service import SELF_SERVICE_EMAIL_DOMAIN

_SELF_EMAIL_SUFFIX = f"@{SELF_SERVICE_EMAIL_DOMAIN}"


def _self_registered_user_filter():
    return User.email.like(f"%{_SELF_EMAIL_SUFFIX}")


def get_dashboard(db: Session) -> AdminDashboardRead:
    today = date.today()

    registered_employees_active = (
        db.query(func.count(User.id))
        .filter(User.is_active.is_(True), _self_registered_user_filter())
        .scalar()
        or 0
    )

    staff_users_active = (
        db.query(func.count(User.id))
        .filter(User.is_active.is_(True), ~_self_registered_user_filter())
        .scalar()
        or 0
    )

    hr_employee_records_active = (
        db.query(func.count(Employee.id))
        .filter(Employee.status == "active", ~Employee.employee_code.like("S%"))
        .scalar()
        or 0
    )

    departments = db.query(func.count(Department.id)).scalar() or 0

    open_job_descriptions = (
        db.query(func.count(JobDescription.id)).filter(JobDescription.status == "open").scalar() or 0
    )

    candidates_pending_review = (
        db.query(func.count(Candidate.id))
        .filter(Candidate.status.in_(("uploaded", "parsed", "scored")))
        .scalar()
        or 0
    )

    attendance_rows = (
        db.query(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .filter(AttendanceRecord.date == today)
        .group_by(AttendanceRecord.status)
        .all()
    )
    status_counts = {status: count for status, count in attendance_rows}
    attendance_today = AttendanceTodaySnapshot(
        present=status_counts.get("present", 0),
        absent=status_counts.get("absent", 0),
        late=status_counts.get("late", 0),
        on_leave=status_counts.get("on_leave", 0),
        half_day=status_counts.get("half_day", 0),
        holiday=status_counts.get("holiday", 0),
        total_marked=sum(status_counts.values()),
    )

    leave_requests_pending = (
        db.query(func.count(LeaveRequest.id)).filter(LeaveRequest.status == "pending").scalar() or 0
    )

    payroll_runs_pending_approval = (
        db.query(func.count(PayrollRun.id))
        .filter(PayrollRun.status == "pending_approval")
        .scalar()
        or 0
    )

    health = integration.health_check()
    registry = db.query(IntegrationRegistry).filter_by(agent_key=integration.AGENT_KEY).one_or_none()
    agent_mode = "registered" if registry and registry.status == "registered" else "standalone"

    return AdminDashboardRead(
        agent_status=health.status,
        agent_mode=agent_mode,  # type: ignore[arg-type]
        registered_employees_active=registered_employees_active,
        staff_users_active=staff_users_active,
        hr_employee_records_active=hr_employee_records_active,
        departments=departments,
        open_job_descriptions=open_job_descriptions,
        candidates_pending_review=candidates_pending_review,
        attendance_today=attendance_today,
        leave_requests_pending=leave_requests_pending,
        payroll_runs_pending_approval=payroll_runs_pending_approval,
    )
