"""Attendance routes — API_ENDPOINTS.md §6."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.exceptions import ValidationFailed
from app.schemas.attendance import (
    AttendanceEmployeesFromExcelCreate,
    AttendanceEmployeesFromExcelResult,
    AttendanceImportResult,
    AttendanceMonthlyGrid,
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
from app.services.attendance_period_report import analyze_period_file, create_employees_from_excel

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


@router.get("/attendance/monthly/grid", response_model=AttendanceMonthlyGrid)
def monthly_attendance_grid(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "read"))],
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    department_id: int | None = None,
) -> AttendanceMonthlyGrid:
    return svc.get_monthly_grid(db, auth, year=year, month=month, department_id=department_id)


@router.post("/attendance", response_model=AttendanceRecordRead, status_code=201)
def create_attendance(
    payload: AttendanceRecordCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> AttendanceRecordRead:
    return AttendanceRecordRead.model_validate(svc.create_record(db, auth, payload))


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
    saturday_off_mode: Annotated[str, Form()] = "second_saturday",
    saturday_off_date: Annotated[str | None, Form()] = None,
) -> AttendancePeriodReport:
    """Upload biometric Excel/CSV and return full office policy report.

    saturday_off_mode:
    - second_saturday (Recommended): 2nd Saturday of each month in the file period
    - date: use saturday_off_date (YYYY-MM-DD) as the company Saturday off
    - auto: Don't know — AI/heuristic picks Saturday(s) from punch patterns
    """
    content = await file.read()
    name = file.filename or "attendance.xlsx"
    parsed_date: date | None = None
    raw = (saturday_off_date or "").strip()
    if raw:
        try:
            parsed_date = date.fromisoformat(raw[:10])
        except ValueError as exc:
            raise ValidationFailed("saturday_off_date must be YYYY-MM-DD") from exc
    return analyze_period_file(
        db,
        auth,
        content,
        name,
        persist=True,
        saturday_off_mode=saturday_off_mode,
        saturday_off_date=parsed_date,
    )


@router.post(
    "/attendance/period-report/create-employees",
    response_model=AttendanceEmployeesFromExcelResult,
)
def create_employees_from_attendance_excel(
    payload: AttendanceEmployeesFromExcelCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> AttendanceEmployeesFromExcelResult:
    return create_employees_from_excel(db, auth, payload)


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


@router.patch("/attendance/{record_id}", response_model=AttendanceRecordRead)
def patch_attendance(
    record_id: int,
    payload: AttendanceRecordUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "write"))],
) -> AttendanceRecordRead:
    return AttendanceRecordRead.model_validate(svc.update_record(db, auth, record_id, payload))


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
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "read"))],
) -> LeaveRequestRead:
    """Self-service employees may submit their own leave (read). HR needs write for others."""
    return LeaveRequestRead.model_validate(svc.create_leave_request(db, auth, payload))


@router.patch("/leave-requests/{leave_id}", response_model=LeaveRequestRead)
def patch_leave(
    leave_id: int,
    payload: LeaveRequestUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("attendance", "approve"))],
) -> LeaveRequestRead:
    return LeaveRequestRead.model_validate(svc.update_leave_request(db, auth, leave_id, payload))
