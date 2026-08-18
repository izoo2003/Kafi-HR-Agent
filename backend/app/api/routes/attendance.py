"""Attendance routes — API_ENDPOINTS.md §6."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.attendance import (
    AttendanceImportResult,
    AttendancePeriodReport,
    AttendanceRecordCreate,
    AttendanceRecordRead,
    AttendanceRecordUpdate,
    AttendanceRuleCreate,
    AttendanceRuleRead,
    AttendanceRuleUpdate,
    AttendanceSummary,
    BiometricSyncResult,
    LeaveRequestCreate,
    LeaveRequestRead,
    LeaveRequestUpdate,
)
from app.schemas.common import AuthContext, PaginatedResponse
from app.services import attendance_service as svc
from app.services.attendance_period_report import analyze_period_file

router = APIRouter(tags=["attendance"])


@router.get("/attendance-rules", response_model=list[AttendanceRuleRead])
def list_rules(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("attendance", "read"))],
) -> list[AttendanceRuleRead]:
    return [AttendanceRuleRead.model_validate(r) for r in svc.list_rules(db)]


@router.post("/attendance-rules", response_model=AttendanceRuleRead, status_code=201)
def create_rule(
    payload: AttendanceRuleCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> AttendanceRuleRead:
    return AttendanceRuleRead.model_validate(svc.create_rule(db, auth, payload))


@router.patch("/attendance-rules/{rule_id}", response_model=AttendanceRuleRead)
def patch_rule(
    rule_id: int,
    payload: AttendanceRuleUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> AttendanceRuleRead:
    return AttendanceRuleRead.model_validate(svc.update_rule(db, auth, rule_id, payload))


@router.get("/attendance", response_model=PaginatedResponse[AttendanceRecordRead])
def list_attendance(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    employee_id: int | None = None,
    department_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PaginatedResponse[AttendanceRecordRead]:
    return svc.list_records(
        db,
        auth,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        department_id=department_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/attendance", response_model=AttendanceRecordRead, status_code=201)
def create_attendance(
    payload: AttendanceRecordCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> AttendanceRecordRead:
    return AttendanceRecordRead.model_validate(svc.create_record(db, auth, payload))


@router.patch("/attendance/{record_id}", response_model=AttendanceRecordRead)
def patch_attendance(
    record_id: int,
    payload: AttendanceRecordUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> AttendanceRecordRead:
    return AttendanceRecordRead.model_validate(svc.update_record(db, auth, record_id, payload))


@router.post("/attendance/import", response_model=AttendanceImportResult)
async def import_attendance(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
    file: UploadFile = File(...),
) -> AttendanceImportResult:
    content = await file.read()
    name = file.filename or "import.csv"
    return svc.import_attendance_csv(db, auth, content, filename=name)


@router.post("/attendance/period-report", response_model=AttendancePeriodReport)
async def attendance_period_report(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
    file: UploadFile = File(...),
) -> AttendancePeriodReport:
    """Upload biometric Excel/CSV (name + date + time) and return full office policy report.

    Applies late/half-day/Saturday-off/auto-holiday/3-lates=1-off/OT/leave rules,
    persists derived attendance rows, and returns per-employee breakdown.
    """
    content = await file.read()
    name = file.filename or "attendance.xlsx"
    return analyze_period_file(db, auth, content, name, persist=True)


@router.post("/attendance/sync-biometric", response_model=BiometricSyncResult)
def sync_biometric(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> BiometricSyncResult:
    return svc.sync_biometric(db, auth)


@router.get("/attendance/summary", response_model=AttendanceSummary)
def summary(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "read"))],
    employee_id: int = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> AttendanceSummary:
    return svc.attendance_summary(
        db,
        auth,
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_end,
    )


@router.get("/leave-requests", response_model=PaginatedResponse[LeaveRequestRead])
def list_leave(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    employee_id: int | None = None,
    status: str | None = None,
    department_id: int | None = None,
) -> PaginatedResponse[LeaveRequestRead]:
    return svc.list_leave_requests(
        db,
        auth,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        status=status,
        department_id=department_id,
    )


@router.post("/leave-requests", response_model=LeaveRequestRead, status_code=201)
def create_leave(
    payload: LeaveRequestCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> LeaveRequestRead:
    return LeaveRequestRead.model_validate(svc.create_leave_request(db, auth, payload))


@router.patch("/leave-requests/{leave_id}", response_model=LeaveRequestRead)
def patch_leave(
    leave_id: int,
    payload: LeaveRequestUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "approve"))],
) -> LeaveRequestRead:
    return LeaveRequestRead.model_validate(svc.update_leave_request(db, auth, leave_id, payload))
