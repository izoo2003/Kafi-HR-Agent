"""Employee Development — resignation letters (generate / send / accept)."""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleViolation, EntityNotFound, PermissionDenied
from app.core.gemini_client import generate_content_with_fallback
from app.core.self_service import is_self_service, own_employee_id
from app.models.employees import Employee
from app.models.identity import User
from app.models.kpi import EmployeeResignationNotice
from app.schemas.common import PERMISSION_RANK, AuthContext
from app.schemas.employee_resignation import (
    EmployeeResignationCreateRequest,
    EmployeeResignationGenerateResponse,
    EmployeeResignationListResponse,
    EmployeeResignationRead,
    EmployeeResignationUpdateRequest,
)
from app.services import audit_service

logger = logging.getLogger(__name__)


def _has_kpi_write(auth: AuthContext) -> bool:
    level = auth.agent_permissions.get("hr_admin.kpi", "none")
    return PERMISSION_RANK.get(level, 0) >= PERMISSION_RANK["write"]


def _resolve_list_employee_id(auth: AuthContext, employee_id: int | None) -> int | None:
    if is_self_service(auth):
        own = own_employee_id(auth)
        if own is None:
            raise PermissionDenied("No linked employee record")
        if employee_id is not None and employee_id != own:
            raise PermissionDenied("You can only view your own resignation notices")
        return own
    return employee_id


def _load_employee(db: Session, employee_id: int) -> Employee:
    emp = (
        db.query(Employee)
        .options(joinedload(Employee.department))
        .filter(Employee.id == employee_id)
        .one_or_none()
    )
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")
    return emp


def _to_read(
    row: EmployeeResignationNotice,
    *,
    employee_name: str | None = None,
    employee_code: str | None = None,
) -> EmployeeResignationRead:
    return EmployeeResignationRead(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=employee_name,
        employee_code=employee_code,
        subject=row.subject,
        letter_body=row.letter_body,
        reason=row.reason,
        effective_date=row.effective_date,
        status=row.status,  # type: ignore[arg-type]
        issued_by=row.issued_by,
        issued_at=row.issued_at,
        accepted_at=row.accepted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _template_letter(emp: Employee, reason: str | None, effective: date | None) -> tuple[str, str]:
    dept = emp.department.name if emp.department else "their department"
    eff = (effective or date.today()).isoformat()
    subject = f"Resignation notice — {emp.full_name}"
    reason_line = (reason or "Mutual agreement / organizational decision").strip()
    body = (
        f"Dear {emp.full_name},\n\n"
        f"This letter confirms the processing of your resignation from your role as "
        f"{emp.role_title} in {dept} at Kafi Commodities.\n\n"
        f"Effective date: {eff}\n"
        f"Reason / context: {reason_line}\n\n"
        "Please review this notice carefully. By accepting this resignation on your "
        "account, you confirm that your employment will end on the effective date, "
        "your employee record will be marked exited, and your login access will be "
        "removed.\n\n"
        "If you have questions, contact HR before accepting.\n\n"
        "Sincerely,\n"
        "Human Resources\n"
        "Kafi Commodities\n"
    )
    return subject, body


def generate_resignation_letter(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int,
    reason: str | None,
    effective_date: date | None,
    settings: Settings | None = None,
) -> EmployeeResignationGenerateResponse:
    if not _has_kpi_write(auth):
        raise PermissionDenied("You need write access to generate resignation letters")
    emp = _load_employee(db, employee_id)
    if emp.status == "terminated":
        raise BusinessRuleViolation("This employee is already terminated")

    settings = settings or get_settings()
    api_keys = settings.resolved_gemini_api_keys()
    subject, body = _template_letter(emp, reason, effective_date)
    dept = emp.department.name if emp.department else "n/a"
    eff = (effective_date or date.today()).isoformat()

    if api_keys:
        prompt = f"""Write a professional HR resignation confirmation letter for Kafi Commodities.
Employee: {emp.full_name} ({emp.employee_code})
Role: {emp.role_title}
Department: {dept}
Effective date: {eff}
Reason / context: {(reason or "Not specified").strip()}

Return STRICT JSON only:
{{"subject":"<short subject line>","letter_body":"<full letter plain text>"}}

Rules:
- Formal, clear, respectful tone.
- State that accepting on the employee portal ends employment and removes login access.
- No markdown fences. Plain text body with newlines.
"""
        try:
            response = generate_content_with_fallback(
                prompt=prompt,
                api_keys=api_keys,
                models=settings.resolved_gemini_models(),
                pool_id="employee_resignation",
            )
            import json
            import re

            raw = (getattr(response, "text", None) or "").strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            subject = str(data.get("subject") or subject).strip()[:300]
            body = str(data.get("letter_body") or body).strip()
        except Exception:
            logger.exception("Resignation AI generate failed; using template")

    return EmployeeResignationGenerateResponse(
        employee_id=emp.id,
        employee_name=emp.full_name,
        subject=subject,
        letter_body=body,
        reason=reason,
        effective_date=effective_date or date.today(),
    )


def create_resignation_notice(
    db: Session,
    auth: AuthContext,
    payload: EmployeeResignationCreateRequest,
) -> EmployeeResignationRead:
    if not _has_kpi_write(auth):
        raise PermissionDenied("You need write access to send resignation letters")
    emp = _load_employee(db, payload.employee_id)
    if emp.status == "terminated":
        raise BusinessRuleViolation("This employee is already terminated")

    pending = (
        db.query(EmployeeResignationNotice)
        .filter(
            EmployeeResignationNotice.employee_id == emp.id,
            EmployeeResignationNotice.status == "pending",
        )
        .count()
    )
    if pending:
        raise BusinessRuleViolation(
            "This employee already has a pending resignation notice. "
            "Cancel or wait for acceptance before sending another."
        )

    now = datetime.now(UTC)
    row = EmployeeResignationNotice(
        employee_id=emp.id,
        subject=payload.subject.strip(),
        letter_body=payload.letter_body.strip(),
        reason=(payload.reason or None),
        effective_date=payload.effective_date or date.today(),
        status="pending",
        issued_by=auth.user_id,
        issued_at=now,
    )
    db.add(row)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.sent",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        after_state={
            "employee_id": emp.id,
            "subject": row.subject,
            "effective_date": str(row.effective_date),
        },
    )
    db.commit()
    db.refresh(row)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)


def list_resignation_notices(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int | None = None,
) -> EmployeeResignationListResponse:
    resolved = _resolve_list_employee_id(auth, employee_id)
    q = (
        db.query(EmployeeResignationNotice, Employee)
        .join(Employee, Employee.id == EmployeeResignationNotice.employee_id)
        .order_by(
            EmployeeResignationNotice.issued_at.desc(),
            EmployeeResignationNotice.id.desc(),
        )
    )
    if resolved is not None:
        q = q.filter(EmployeeResignationNotice.employee_id == resolved)
    rows = q.all()
    items = [
        _to_read(n, employee_name=e.full_name, employee_code=e.employee_code)
        for n, e in rows
    ]
    return EmployeeResignationListResponse(items=items, total=len(items))


def get_resignation_notice(
    db: Session, auth: AuthContext, notice_id: int
) -> EmployeeResignationRead:
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if is_self_service(auth):
        own = own_employee_id(auth)
        if own is None or row.employee_id != own:
            raise PermissionDenied("You can only view your own resignation notices")
    emp = _load_employee(db, row.employee_id)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)


def update_resignation_notice(
    db: Session,
    auth: AuthContext,
    notice_id: int,
    payload: EmployeeResignationUpdateRequest,
) -> EmployeeResignationRead:
    if not _has_kpi_write(auth):
        raise PermissionDenied("You need write access to edit resignation notices")
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if row.status == "accepted":
        raise BusinessRuleViolation("Accepted resignations cannot be edited")

    before = {"subject": row.subject, "status": row.status}
    data = payload.model_dump(exclude_unset=True)
    if "subject" in data and data["subject"] is not None:
        row.subject = data["subject"].strip()
    if "letter_body" in data and data["letter_body"] is not None:
        row.letter_body = data["letter_body"].strip()
    if "reason" in data:
        row.reason = data["reason"]
    if "effective_date" in data:
        row.effective_date = data["effective_date"]
    if data.get("status") == "cancelled":
        if row.status != "pending":
            raise BusinessRuleViolation("Only pending notices can be cancelled")
        row.status = "cancelled"

    emp = _load_employee(db, row.employee_id)
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.updated",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        before_state=before,
        after_state={"subject": row.subject, "status": row.status},
    )
    db.commit()
    db.refresh(row)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)


def delete_resignation_notice(db: Session, auth: AuthContext, notice_id: int) -> None:
    if not _has_kpi_write(auth):
        raise PermissionDenied("You need write access to delete resignation notices")
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if row.status == "accepted":
        raise BusinessRuleViolation("Accepted resignations cannot be deleted")
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.deleted",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        before_state={"employee_id": row.employee_id, "status": row.status},
    )
    db.delete(row)
    db.commit()


def accept_resignation_notice(
    db: Session, auth: AuthContext, notice_id: int
) -> EmployeeResignationRead:
    """Employee accepts → terminate employee + deactivate login (hidden from active users)."""
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if row.status != "pending":
        raise BusinessRuleViolation("Only pending resignation notices can be accepted")

    if is_self_service(auth):
        own = own_employee_id(auth)
        if own is None or row.employee_id != own:
            raise PermissionDenied("You can only accept your own resignation notice")
    elif not _has_kpi_write(auth):
        raise PermissionDenied("Insufficient permission to accept this resignation")

    emp = _load_employee(db, row.employee_id)
    now = datetime.now(UTC)
    exit_day = row.effective_date or date.today()

    row.status = "accepted"
    row.accepted_at = now

    if emp.status != "terminated":
        emp.status = "terminated"
        emp.date_exited = exit_day

    linked_user: User | None = None
    if emp.user_id is not None:
        linked_user = db.query(User).filter(User.id == emp.user_id).one_or_none()
        if linked_user is not None and linked_user.is_active:
            linked_user.is_active = False

    # Unlink so the exited employee no longer maps to a login for self-service
    emp.user_id = None

    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.accepted",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        after_state={
            "employee_id": emp.id,
            "user_id": linked_user.id if linked_user else None,
            "employee_status": emp.status,
            "date_exited": str(emp.date_exited),
            "user_deactivated": bool(linked_user),
        },
    )
    db.commit()
    db.refresh(row)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)
