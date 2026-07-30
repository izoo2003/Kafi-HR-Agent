"""Attendance business logic — single status-derivation path for all intake sources."""
from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    EntityNotFound,
    ValidationFailed,
)
from app.ingestion.biometric_client_stub import fetch_punches
from app.models.attendance import AttendanceRecord, AttendanceRule, LeaveRequest
from app.models.employees import Employee
from app.models.system import SystemConfig
from app.schemas.attendance import (
    AttendanceImportResult,
    AttendanceRecordCreate,
    AttendanceRecordRead,
    AttendanceRecordUpdate,
    AttendanceRuleCreate,
    AttendanceRuleUpdate,
    AttendanceSummary,
    BiometricSyncResult,
    ImportErrorRow,
    LeaveRequestCreate,
    LeaveRequestRead,
    LeaveRequestUpdate,
)
from app.schemas.common import AuthContext, PaginatedResponse
from app.services import audit_service


def _company_tz(db: Session) -> ZoneInfo:
    row = db.query(SystemConfig).filter(SystemConfig.key == "attendance.timezone").one_or_none()
    name = "Asia/Karachi"
    if row and isinstance(row.value, dict) and row.value.get("tz"):
        name = str(row.value["tz"])
    elif row and isinstance(row.value, str):
        name = row.value
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _holiday_dates(db: Session) -> set[date]:
    row = db.query(SystemConfig).filter(SystemConfig.key == "attendance.holidays").one_or_none()
    if not row or not isinstance(row.value, list):
        return set()
    out: set[date] = set()
    for item in row.value:
        try:
            out.add(date.fromisoformat(str(item)))
        except ValueError:
            continue
    return out


def get_applicable_rule(db: Session, employee: Employee) -> AttendanceRule:
    dept_rule = (
        db.query(AttendanceRule)
        .filter(AttendanceRule.applies_to_department_id == employee.department_id)
        .order_by(AttendanceRule.id.desc())
        .first()
    )
    if dept_rule:
        return dept_rule
    company = (
        db.query(AttendanceRule)
        .filter(AttendanceRule.applies_to_department_id.is_(None))
        .order_by(AttendanceRule.id.desc())
        .first()
    )
    if company is None:
        raise BusinessRuleViolation(
            "No attendance rule configured — create a company-wide rule first"
        )
    return company


def is_on_approved_leave(db: Session, employee_id: int, on_date: date) -> bool:
    q = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date <= on_date,
            LeaveRequest.end_date >= on_date,
        )
        .first()
    )
    return q is not None


def derive_status(
    *,
    check_in: datetime | None,
    check_out: datetime | None,
    on_leave: bool,
    is_holiday: bool,
    rule: AttendanceRule,
    tz: ZoneInfo,
) -> str:
    """Single status-derivation function — FEATURE_ATTENDANCE.md §2."""
    if on_leave:
        return "on_leave"
    if is_holiday:
        return "holiday"
    if check_in is None and check_out is None:
        return "absent"

    # Compare in company-local time
    def local(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(tz)

    if check_in is None or check_out is None:
        # Incomplete punch pair — treat as half_day if one side present, else absent
        return "half_day" if check_in or check_out else "absent"

    cin = local(check_in)
    cout = local(check_out)
    shift_start_dt = datetime.combine(cin.date(), rule.shift_start, tzinfo=tz)
    minutes_late = max(0, int((cin - shift_start_dt).total_seconds() // 60))
    minutes_present = max(0, int((cout - cin).total_seconds() // 60))

    if minutes_late > rule.grace_period_minutes:
        return "late"
    if minutes_present < rule.half_day_threshold_minutes:
        return "half_day"
    return "present"


def overtime_hours_for_record(
    check_out: datetime | None, rule: AttendanceRule, on_date: date, tz: ZoneInfo
) -> float:
    if check_out is None:
        return 0.0
    if check_out.tzinfo is None:
        check_out = check_out.replace(tzinfo=UTC)
    local_out = check_out.astimezone(tz)
    shift_end_dt = datetime.combine(on_date, rule.shift_end, tzinfo=tz)
    extra = (local_out - shift_end_dt).total_seconds() / 3600.0
    return round(max(0.0, extra), 2)


def _apply_derived_status(db: Session, record: AttendanceRecord, employee: Employee) -> None:
    rule = get_applicable_rule(db, employee)
    tz = _company_tz(db)
    holidays = _holiday_dates(db)
    record.status = derive_status(
        check_in=record.check_in,
        check_out=record.check_out,
        on_leave=is_on_approved_leave(db, record.employee_id, record.date),
        is_holiday=record.date in holidays,
        rule=rule,
        tz=tz,
    )


# --- Rules ---


def list_rules(db: Session) -> list[AttendanceRule]:
    return db.query(AttendanceRule).order_by(AttendanceRule.id).all()


def create_rule(db: Session, auth: AuthContext, payload: AttendanceRuleCreate) -> AttendanceRule:
    rule = AttendanceRule(**payload.model_dump())
    db.add(rule)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="attendance_rule.created",
        entity_type="attendance_rule",
        entity_id=rule.id,
        after_state={"name": rule.name},
    )
    return rule


def update_rule(
    db: Session, auth: AuthContext, rule_id: int, payload: AttendanceRuleUpdate
) -> AttendanceRule:
    rule = db.query(AttendanceRule).filter(AttendanceRule.id == rule_id).one_or_none()
    if rule is None:
        raise EntityNotFound(f"Attendance rule {rule_id} not found")
    before = {"name": rule.name, "grace_period_minutes": rule.grace_period_minutes}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(rule, k, v)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="attendance_rule.updated",
        entity_type="attendance_rule",
        entity_id=rule.id,
        before_state=before,
        after_state=data,
    )
    return rule


# --- Records ---


def list_records(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    employee_id: int | None = None,
    department_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> PaginatedResponse[AttendanceRecordRead]:
    q = db.query(AttendanceRecord).join(Employee, Employee.id == AttendanceRecord.employee_id)
    if employee_id is not None:
        q = q.filter(AttendanceRecord.employee_id == employee_id)
    if department_id is not None:
        q = q.filter(Employee.department_id == department_id)
    if date_from is not None:
        q = q.filter(AttendanceRecord.date >= date_from)
    if date_to is not None:
        q = q.filter(AttendanceRecord.date <= date_to)
    # hide terminated from default views when no employee filter
    if employee_id is None:
        q = q.filter(Employee.status != "terminated")
    total = q.count()
    rows = (
        q.order_by(AttendanceRecord.date.desc(), AttendanceRecord.employee_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=[AttendanceRecordRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_record(
    db: Session, auth: AuthContext, payload: AttendanceRecordCreate, *, source: str = "manual"
) -> AttendanceRecord:
    emp = db.query(Employee).filter(Employee.id == payload.employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {payload.employee_id} not found")
    existing = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id == payload.employee_id,
            AttendanceRecord.date == payload.date,
        )
        .one_or_none()
    )
    if existing:
        raise ConflictError(
            "Attendance record already exists for this employee and date. Edit the existing record instead.",
            details={"existing_id": existing.id},
        )
    record = AttendanceRecord(
        employee_id=payload.employee_id,
        date=payload.date,
        check_in=payload.check_in,
        check_out=payload.check_out,
        source=source,
        notes=payload.notes,
        status="absent",
    )
    _apply_derived_status(db, record, emp)
    db.add(record)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="attendance.created",
        entity_type="attendance_record",
        entity_id=record.id,
        after_state={"date": str(record.date), "status": record.status, "source": source},
    )
    return record


def update_record(
    db: Session, auth: AuthContext, record_id: int, payload: AttendanceRecordUpdate
) -> AttendanceRecord:
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).one_or_none()
    if record is None:
        raise EntityNotFound(f"Attendance record {record_id} not found")
    emp = db.query(Employee).filter(Employee.id == record.employee_id).one()
    before = {
        "check_in": record.check_in.isoformat() if record.check_in else None,
        "check_out": record.check_out.isoformat() if record.check_out else None,
        "status": record.status,
    }
    data = payload.model_dump(exclude_unset=True)
    reason = data.pop("reason", None)
    for k, v in data.items():
        setattr(record, k, v)
    _apply_derived_status(db, record, emp)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="attendance.manual_edit",
        entity_type="attendance_record",
        entity_id=record.id,
        before_state=before,
        after_state={
            "check_in": record.check_in.isoformat() if record.check_in else None,
            "check_out": record.check_out.isoformat() if record.check_out else None,
            "status": record.status,
            "reason": reason,
        },
    )
    return record


# --- Leave ---


def _leave_overlaps(
    db: Session, employee_id: int, start: date, end: date, exclude_id: int | None = None
) -> bool:
    q = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status.in_(["pending", "approved"]),
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date >= start,
    )
    if exclude_id is not None:
        q = q.filter(LeaveRequest.id != exclude_id)
    return q.first() is not None


def list_leave_requests(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    employee_id: int | None = None,
    status: str | None = None,
    department_id: int | None = None,
) -> PaginatedResponse[LeaveRequestRead]:
    q = db.query(LeaveRequest).join(Employee, Employee.id == LeaveRequest.employee_id)
    if employee_id is not None:
        q = q.filter(LeaveRequest.employee_id == employee_id)
    if status is not None:
        q = q.filter(LeaveRequest.status == status)
    if department_id is not None:
        q = q.filter(Employee.department_id == department_id)
    total = q.count()
    rows = (
        q.order_by(LeaveRequest.start_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=[LeaveRequestRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_leave_request(
    db: Session, auth: AuthContext, payload: LeaveRequestCreate
) -> LeaveRequest:
    if payload.end_date < payload.start_date:
        raise ValidationFailed("end_date must be on or after start_date")
    if db.query(Employee).filter(Employee.id == payload.employee_id).one_or_none() is None:
        raise EntityNotFound("Employee not found")
    if _leave_overlaps(db, payload.employee_id, payload.start_date, payload.end_date):
        raise BusinessRuleViolation(
            "Leave request overlaps an existing pending or approved leave for this employee"
        )
    row = LeaveRequest(**payload.model_dump(), status="pending")
    db.add(row)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="leave_request.created",
        entity_type="leave_request",
        entity_id=row.id,
        after_state={"employee_id": row.employee_id, "start": str(row.start_date), "end": str(row.end_date)},
    )
    return row


def update_leave_request(
    db: Session, auth: AuthContext, leave_id: int, payload: LeaveRequestUpdate
) -> LeaveRequest:
    row = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"Leave request {leave_id} not found")
    if row.status != "pending":
        raise BusinessRuleViolation("Only pending leave requests can be approved or rejected")
    before = {"status": row.status}
    row.status = payload.status
    row.approved_by = auth.user_id
    if payload.reason:
        row.reason = payload.reason
    db.flush()

    # Refresh attendance status for each day in range when approved
    if payload.status == "approved":
        emp = db.query(Employee).filter(Employee.id == row.employee_id).one()
        d = row.start_date
        while d <= row.end_date:
            rec = (
                db.query(AttendanceRecord)
                .filter(AttendanceRecord.employee_id == row.employee_id, AttendanceRecord.date == d)
                .one_or_none()
            )
            if rec is None:
                rec = AttendanceRecord(
                    employee_id=row.employee_id,
                    date=d,
                    source="manual",
                    status="on_leave",
                    notes="Auto-created from approved leave",
                )
                db.add(rec)
            _apply_derived_status(db, rec, emp)
            d += timedelta(days=1)
        db.flush()

    action = f"leave_request.{payload.status}"
    audit_service.log_from_auth(
        db,
        auth,
        action=action,
        entity_type="leave_request",
        entity_id=row.id,
        before_state=before,
        after_state={"status": row.status},
    )
    return row


# --- Summary ---


def attendance_summary(
    db: Session,
    *,
    employee_id: int,
    period_start: date,
    period_end: date,
) -> AttendanceSummary:
    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")
    rule = get_applicable_rule(db, emp)
    tz = _company_tz(db)

    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date >= period_start,
            AttendanceRecord.date <= period_end,
        )
        .all()
    )
    by_date = {r.date: r for r in records}

    days_present = days_late = days_half = days_absent = days_leave = 0
    overtime = 0.0
    total_working = 0
    holidays = _holiday_dates(db)

    d = period_start
    while d <= period_end:
        # Skip pure weekends? Spec doesn't say — count all calendar days as working days
        # except holidays. Keep simple: every non-holiday day is a working day.
        if d in holidays:
            d += timedelta(days=1)
            continue
        total_working += 1
        rec = by_date.get(d)
        status = rec.status if rec else (
            "on_leave" if is_on_approved_leave(db, employee_id, d) else "absent"
        )
        if status == "present":
            days_present += 1
        elif status == "late":
            days_late += 1
        elif status == "half_day":
            days_half += 1
        elif status == "on_leave":
            days_leave += 1
        elif status == "absent":
            days_absent += 1
        if rec:
            overtime += overtime_hours_for_record(rec.check_out, rule, d, tz)
        d += timedelta(days=1)

    return AttendanceSummary(
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_end,
        days_present=days_present,
        days_late=days_late,
        days_half_day=days_half,
        days_absent=days_absent,
        days_on_leave=days_leave,
        total_working_days=total_working,
        overtime_hours=round(overtime, 2),
    )


# --- Import ---


def _parse_dt(value: str, on_date: date, tz: ZoneInfo) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    # Accept ISO datetime or time-only HH:MM / HH:MM:SS
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz).astimezone(UTC)
        return dt
    except ValueError:
        pass
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            t = datetime.strptime(value, fmt).time()
            return datetime.combine(on_date, t, tzinfo=tz).astimezone(UTC)
        except ValueError:
            continue
    raise ValueError(f"Invalid datetime: {value}")


def import_attendance_csv(
    db: Session, auth: AuthContext, content: bytes, filename: str = "import.csv"
) -> AttendanceImportResult:
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValidationFailed("CSV has no header row")
    # normalize headers
    field_map = {h.strip().lower(): h for h in reader.fieldnames}
    required = ["employee_code", "date", "check_in", "check_out"]
    for req in required:
        if req not in field_map:
            raise ValidationFailed(f"Missing required column: {req}")

    tz = _company_tz(db)
    imported = 0
    errors: list[ImportErrorRow] = []
    row_num = 1  # header is row 1
    for raw in reader:
        row_num += 1
        try:
            code = (raw[field_map["employee_code"]] or "").strip()
            emp = db.query(Employee).filter(Employee.employee_code == code).one_or_none()
            if emp is None or emp.status == "terminated":
                raise ValueError(f"Unknown or terminated employee_code: {code}")
            on_date = date.fromisoformat((raw[field_map["date"]] or "").strip())
            cin = _parse_dt(raw[field_map["check_in"]], on_date, tz)
            cout = _parse_dt(raw[field_map["check_out"]], on_date, tz)
            existing = (
                db.query(AttendanceRecord)
                .filter(AttendanceRecord.employee_id == emp.id, AttendanceRecord.date == on_date)
                .one_or_none()
            )
            if existing:
                existing.check_in = cin
                existing.check_out = cout
                existing.source = "import"
                _apply_derived_status(db, existing, emp)
            else:
                rec = AttendanceRecord(
                    employee_id=emp.id,
                    date=on_date,
                    check_in=cin,
                    check_out=cout,
                    source="import",
                    status="absent",
                )
                _apply_derived_status(db, rec, emp)
                db.add(rec)
            imported += 1
        except Exception as exc:  # noqa: BLE001 — collect per-row
            errors.append(ImportErrorRow(row=row_num, message=str(exc)))
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="attendance.imported",
        entity_type="attendance_import",
        entity_id=0,
        after_state={"imported": imported, "errors": len(errors), "filename": filename},
    )
    return AttendanceImportResult(imported=imported, errors=errors)


def sync_biometric(db: Session, auth: AuthContext) -> BiometricSyncResult:
    punches = fetch_punches(datetime.now(UTC) - timedelta(days=1))
    _ = auth
    _ = db
    return BiometricSyncResult(
        message="Biometric device not yet connected - use manual import.",
        punches_fetched=len(punches),
    )


def ensure_default_rule(db: Session) -> None:
    if db.query(AttendanceRule).count() == 0:
        db.add(
            AttendanceRule(
                name="standard_9to6",
                shift_start=time(9, 0),
                shift_end=time(18, 0),
                grace_period_minutes=15,
                half_day_threshold_minutes=240,
                applies_to_department_id=None,
            )
        )


def ensure_attendance_config(db: Session) -> None:
    if db.query(SystemConfig).filter_by(key="attendance.timezone").one_or_none() is None:
        db.add(SystemConfig(key="attendance.timezone", value={"tz": "Asia/Karachi"}))
    if db.query(SystemConfig).filter_by(key="attendance.holidays").one_or_none() is None:
        db.add(SystemConfig(key="attendance.holidays", value=[]))
