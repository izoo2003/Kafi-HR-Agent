"""Employee Development — resignation letters (HR-issued or employee-authored)."""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleViolation, EntityNotFound, PermissionDenied
from app.core.gemini_client import generate_content_with_fallback
from app.core.self_service import is_self_service, own_employee_id
from app.models.employees import Employee
from app.models.identity import AgentAccessMatrix, User, UserRole
from app.models.kpi import EmployeeResignationNotice
from app.schemas.common import PERMISSION_RANK, AuthContext
from app.schemas.employee_resignation import (
    EmployeeResignationCreateRequest,
    EmployeeResignationGenerateResponse,
    EmployeeResignationListResponse,
    EmployeeResignationRead,
    EmployeeResignationRejectRequest,
    EmployeeResignationUpdateRequest,
)
from app.services import audit_service

logger = logging.getLogger(__name__)

EMPLOYEE_OPEN_STATUSES = ("draft", "pending", "rejected")
HR_OPEN_STATUSES = ("pending",)


def ensure_resignation_schema(db: Session) -> None:
    """create_all will not add columns on existing tables."""
    bind = db.get_bind()
    if bind is None:
        return
    dialect = bind.dialect.name
    cols = [
        ("direction", "VARCHAR(32) DEFAULT 'hr'"),
        ("rejected_at", "TIMESTAMP"),
        ("rejection_reason", "TEXT"),
        ("reviewed_by", "INTEGER"),
    ]
    if dialect == "sqlite":
        existing = {
            row[1]
            for row in db.execute(text("PRAGMA table_info(employee_resignation_notices)")).fetchall()
        }
        if not existing:
            return
        for name, ddl in cols:
            if name not in existing:
                db.execute(text(f"ALTER TABLE employee_resignation_notices ADD COLUMN {name} {ddl}"))
        db.execute(
            text(
                "UPDATE employee_resignation_notices SET direction = 'hr' "
                "WHERE direction IS NULL OR direction = ''"
            )
        )
        return
    if dialect == "postgresql":

        def _has_column(column: str) -> bool:
            return (
                db.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = "
                        "'employee_resignation_notices' AND column_name = :c"
                    ),
                    {"c": column},
                ).scalar()
                is not None
            )

        mapping = {
            "direction": "VARCHAR(32) DEFAULT 'hr'",
            "rejected_at": "TIMESTAMPTZ",
            "rejection_reason": "TEXT",
            "reviewed_by": "INTEGER",
        }
        for name, ddl in mapping.items():
            if not _has_column(name):
                db.execute(
                    text(
                        f"ALTER TABLE employee_resignation_notices "
                        f"ADD COLUMN IF NOT EXISTS {name} {ddl}"
                    )
                )
        db.execute(
            text(
                "UPDATE employee_resignation_notices SET direction = 'hr' "
                "WHERE direction IS NULL OR direction = ''"
            )
        )


def _has_kpi_write(auth: AuthContext) -> bool:
    level = auth.agent_permissions.get("hr_admin.kpi", "none")
    return PERMISSION_RANK.get(level, 0) >= PERMISSION_RANK["write"]


def _is_hr(auth: AuthContext) -> bool:
    return _has_kpi_write(auth) and not is_self_service(auth)


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
    direction = (row.direction or "hr") if hasattr(row, "direction") else "hr"
    if direction not in ("hr", "employee"):
        direction = "hr"
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
        direction=direction,  # type: ignore[arg-type]
        issued_by=row.issued_by,
        issued_at=row.issued_at,
        accepted_at=row.accepted_at,
        rejected_at=getattr(row, "rejected_at", None),
        rejection_reason=getattr(row, "rejection_reason", None),
        reviewed_by=getattr(row, "reviewed_by", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _open_count(db: Session, employee_id: int, *, direction: str) -> int:
    statuses = EMPLOYEE_OPEN_STATUSES if direction == "employee" else HR_OPEN_STATUSES
    return (
        db.query(EmployeeResignationNotice)
        .filter(
            EmployeeResignationNotice.employee_id == employee_id,
            EmployeeResignationNotice.direction == direction,
            EmployeeResignationNotice.status.in_(statuses),
        )
        .count()
    )


def _hr_reviewers(db: Session, *, exclude_user_id: int | None = None) -> list[User]:
    role_ids = {
        m.role_id
        for m in db.query(AgentAccessMatrix)
        .filter(
            AgentAccessMatrix.agent_key == "hr_admin",
            AgentAccessMatrix.module_key == "kpi",
        )
        .all()
        if PERMISSION_RANK.get(m.permission, 0) >= PERMISSION_RANK["write"]
    }
    emp_read_roles = {
        m.role_id
        for m in db.query(AgentAccessMatrix)
        .filter(
            AgentAccessMatrix.agent_key == "hr_admin",
            AgentAccessMatrix.module_key == "employees",
        )
        .all()
        if PERMISSION_RANK.get(m.permission, 0) >= PERMISSION_RANK["read"]
    }
    role_ids &= emp_read_roles
    if not role_ids:
        return []
    user_ids = {
        ur.user_id for ur in db.query(UserRole).filter(UserRole.role_id.in_(role_ids)).all()
    }
    if exclude_user_id is not None:
        user_ids.discard(exclude_user_id)
    if not user_ids:
        return []
    return db.query(User).filter(User.id.in_(user_ids), User.is_active.is_(True)).all()


def _notify_hr_of_submission(db: Session, emp: Employee, notice: EmployeeResignationNotice) -> None:
    from app.services import notification_service

    reviewers = _hr_reviewers(db, exclude_user_id=notice.issued_by)
    if not reviewers:
        return
    notification_service.create_for_users(
        db,
        users=reviewers,
        title=f"Resignation submitted — {emp.full_name}",
        body=(
            f"{emp.full_name} ({emp.employee_code}) sent a resignation letter for HR review. "
            "Open Employee Development → Resignation to accept or reject it."
        ),
        kind="resignation_submitted",
        payload={"notice_id": notice.id, "employee_id": emp.id},
    )


def _notify_employee(db: Session, emp: Employee, *, title: str, body: str, kind: str, payload: dict) -> None:
    from app.services import notification_service

    if emp.user_id is None:
        return
    user = db.query(User).filter(User.id == emp.user_id, User.is_active.is_(True)).one_or_none()
    if user is None:
        return
    notification_service.create_for_users(
        db,
        users=[user],
        title=title,
        body=body,
        kind=kind,
        payload=payload,
    )


def _hr_template_letter(emp: Employee, reason: str | None, effective: date | None) -> tuple[str, str]:
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


def _employee_template_letter(
    emp: Employee, reason: str | None, effective: date | None
) -> tuple[str, str]:
    dept = emp.department.name if emp.department else "my department"
    eff = (effective or date.today()).isoformat()
    subject = f"Resignation — {emp.full_name}"
    reason_line = (reason or "Personal reasons").strip()
    body = (
        "Dear HR,\n\n"
        f"Please accept this letter as formal notice of my resignation from my position as "
        f"{emp.role_title} in {dept} at Kafi Commodities.\n\n"
        f"My last working day will be {eff}.\n"
        f"Reason: {reason_line}\n\n"
        "I will complete a proper handover of my responsibilities and remain available "
        "to support the transition.\n\n"
        "Thank you for the opportunity to work at KAFI.\n\n"
        "Sincerely,\n"
        f"{emp.full_name}\n"
        f"{emp.employee_code}\n"
    )
    return subject, body


def generate_resignation_letter(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int | None,
    reason: str | None,
    effective_date: date | None,
    settings: Settings | None = None,
) -> EmployeeResignationGenerateResponse:
    employee_authored = is_self_service(auth)
    if employee_authored:
        own = own_employee_id(auth)
        if own is None:
            raise PermissionDenied("No linked employee record")
        if employee_id is not None and employee_id != own:
            raise PermissionDenied("You can only generate your own resignation letter")
        target_id = own
    else:
        if not _has_kpi_write(auth):
            raise PermissionDenied("You need write access to generate resignation letters")
        if employee_id is None:
            raise BusinessRuleViolation("Select an employee")
        target_id = employee_id

    emp = _load_employee(db, target_id)
    if emp.status == "terminated":
        raise BusinessRuleViolation("This employee is already terminated")

    settings = settings or get_settings()
    api_keys = settings.resolved_gemini_api_keys()
    if employee_authored:
        subject, body = _employee_template_letter(emp, reason, effective_date)
    else:
        subject, body = _hr_template_letter(emp, reason, effective_date)
    dept = emp.department.name if emp.department else "n/a"
    eff = (effective_date or date.today()).isoformat()

    if api_keys:
        if employee_authored:
            prompt = f"""Write a professional first-person resignation letter from an employee at Kafi Commodities.
Employee: {emp.full_name} ({emp.employee_code})
Role: {emp.role_title}
Department: {dept}
Last working day: {eff}
Reason: {(reason or "Not specified").strip()}

Return STRICT JSON only:
{{"subject":"<short subject line>","letter_body":"<full letter plain text>"}}

Rules:
- Written in the first person from the employee to HR.
- Formal, clear, respectful. Ask HR to accept the resignation.
- Mention last working day and willingness to handover.
- No markdown fences. Plain text body with newlines.
"""
        else:
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
        direction="employee" if employee_authored else "hr",
    )


def create_resignation_notice(
    db: Session,
    auth: AuthContext,
    payload: EmployeeResignationCreateRequest,
) -> EmployeeResignationRead:
    employee_authored = is_self_service(auth)
    if employee_authored:
        own = own_employee_id(auth)
        if own is None:
            raise PermissionDenied("No linked employee record")
        target_id = own
        direction = "employee"
        status = "pending" if payload.submit else "draft"
    else:
        if not _has_kpi_write(auth):
            raise PermissionDenied("You need write access to send resignation letters")
        if payload.employee_id is None:
            raise BusinessRuleViolation("Select an employee")
        target_id = payload.employee_id
        direction = "hr"
        status = "pending"

    emp = _load_employee(db, target_id)
    if emp.status == "terminated":
        raise BusinessRuleViolation("This employee is already terminated")

    if _open_count(db, emp.id, direction=direction):
        if direction == "employee":
            raise BusinessRuleViolation(
                "You already have a resignation letter in progress. "
                "Edit, withdraw, or wait for HR before creating another."
            )
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
        status=status,
        direction=direction,
        issued_by=auth.user_id,
        issued_at=now,
    )
    db.add(row)
    db.flush()
    if status == "pending" and direction == "employee":
        _notify_hr_of_submission(db, emp, row)
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.sent" if status == "pending" else "employee_resignation.drafted",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        after_state={
            "employee_id": emp.id,
            "subject": row.subject,
            "direction": direction,
            "status": status,
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
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if row.status == "accepted":
        raise BusinessRuleViolation("Accepted resignations cannot be edited")

    direction = row.direction or "hr"
    if is_self_service(auth):
        own = own_employee_id(auth)
        if own is None or row.employee_id != own:
            raise PermissionDenied("You can only edit your own resignation letter")
        if direction != "employee":
            raise PermissionDenied("You cannot edit an HR-issued resignation notice")
        if row.status not in ("draft", "rejected"):
            raise BusinessRuleViolation(
                "Only a draft or rejected letter can be edited. Withdraw it from HR first if it is pending."
            )
        if payload.status == "cancelled":
            raise PermissionDenied("You cannot cancel this notice that way — withdraw or delete the draft")
    else:
        if not _has_kpi_write(auth):
            raise PermissionDenied("You need write access to edit resignation notices")
        if direction == "employee" and payload.status != "cancelled":
            raise PermissionDenied("Employee-authored letters are edited by the employee")
        if payload.status == "cancelled" and direction == "employee":
            raise BusinessRuleViolation("Reject an employee resignation instead of cancelling it")

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
        if row.status != "pending" or direction != "hr":
            raise BusinessRuleViolation("Only pending HR notices can be cancelled")
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


def submit_resignation_notice(
    db: Session, auth: AuthContext, notice_id: int
) -> EmployeeResignationRead:
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if not is_self_service(auth):
        raise PermissionDenied("Only the employee can send their letter to HR")
    own = own_employee_id(auth)
    if own is None or row.employee_id != own:
        raise PermissionDenied("You can only send your own resignation letter")
    if (row.direction or "hr") != "employee":
        raise BusinessRuleViolation("This is an HR-issued notice")
    if row.status not in ("draft", "rejected"):
        raise BusinessRuleViolation("Only a draft or rejected letter can be sent to HR")

    row.status = "pending"
    row.rejected_at = None
    row.rejection_reason = None
    row.reviewed_by = None
    emp = _load_employee(db, row.employee_id)
    _notify_hr_of_submission(db, emp, row)
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.submitted",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        after_state={"employee_id": emp.id, "subject": row.subject},
    )
    db.commit()
    db.refresh(row)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)


def withdraw_resignation_notice(
    db: Session, auth: AuthContext, notice_id: int
) -> EmployeeResignationRead:
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if not is_self_service(auth):
        raise PermissionDenied("Only the employee can withdraw their letter")
    own = own_employee_id(auth)
    if own is None or row.employee_id != own:
        raise PermissionDenied("You can only withdraw your own resignation letter")
    if (row.direction or "hr") != "employee" or row.status != "pending":
        raise BusinessRuleViolation("Only a letter pending HR review can be withdrawn")
    row.status = "draft"
    emp = _load_employee(db, row.employee_id)
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.withdrawn",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
    )
    db.commit()
    db.refresh(row)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)


def delete_resignation_notice(db: Session, auth: AuthContext, notice_id: int) -> None:
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if row.status == "accepted":
        raise BusinessRuleViolation("Accepted resignations cannot be deleted")
    direction = row.direction or "hr"
    if is_self_service(auth):
        own = own_employee_id(auth)
        if own is None or row.employee_id != own:
            raise PermissionDenied("You can only delete your own draft")
        if direction != "employee" or row.status not in ("draft", "rejected"):
            raise BusinessRuleViolation("Only a draft or rejected letter can be deleted")
    else:
        if not _has_kpi_write(auth):
            raise PermissionDenied("You need write access to delete resignation notices")
        if direction == "employee":
            raise PermissionDenied("Employee-authored letters are deleted by the employee")
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.deleted",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        before_state={"employee_id": row.employee_id, "status": row.status, "direction": direction},
    )
    db.delete(row)
    db.commit()


def _apply_termination(db: Session, emp: Employee, exit_day: date) -> User | None:
    if emp.status != "terminated":
        emp.status = "terminated"
        emp.date_exited = exit_day
    linked_user: User | None = None
    if emp.user_id is not None:
        linked_user = db.query(User).filter(User.id == emp.user_id).one_or_none()
        if linked_user is not None and linked_user.is_active:
            linked_user.is_active = False
    emp.user_id = None
    return linked_user


def accept_resignation_notice(
    db: Session, auth: AuthContext, notice_id: int
) -> EmployeeResignationRead:
    """HR-issued: employee accepts. Employee-authored: HR accepts. Then terminate + deactivate login."""
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if row.status != "pending":
        raise BusinessRuleViolation("Only pending resignation notices can be accepted")

    direction = row.direction or "hr"
    if direction == "employee":
        if not _is_hr(auth):
            raise PermissionDenied("HR must accept an employee-submitted resignation")
    elif is_self_service(auth):
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
    if direction == "employee":
        row.reviewed_by = auth.user_id
        row.rejected_at = None
        row.rejection_reason = None
    linked_user = _apply_termination(db, emp, exit_day)

    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.accepted",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        after_state={
            "employee_id": emp.id,
            "direction": direction,
            "user_id": linked_user.id if linked_user else None,
            "employee_status": emp.status,
            "date_exited": str(emp.date_exited),
            "user_deactivated": bool(linked_user),
        },
    )
    db.commit()
    db.refresh(row)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)


def reject_resignation_notice(
    db: Session,
    auth: AuthContext,
    notice_id: int,
    payload: EmployeeResignationRejectRequest,
) -> EmployeeResignationRead:
    if not _is_hr(auth):
        raise PermissionDenied("Only HR can reject an employee resignation")
    row = (
        db.query(EmployeeResignationNotice)
        .filter(EmployeeResignationNotice.id == notice_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Resignation notice {notice_id} not found")
    if (row.direction or "hr") != "employee" or row.status != "pending":
        raise BusinessRuleViolation("Only an employee letter pending HR review can be rejected")

    now = datetime.now(UTC)
    row.status = "rejected"
    row.rejected_at = now
    row.reviewed_by = auth.user_id
    row.rejection_reason = (payload.reason or "").strip() or None
    emp = _load_employee(db, row.employee_id)
    reason_note = f" Reason: {row.rejection_reason}" if row.rejection_reason else ""
    _notify_employee(
        db,
        emp,
        title="Resignation letter rejected",
        body=(
            "HR rejected your resignation letter."
            f"{reason_note} "
            "You can edit it and send it again from Employee Development → Resignation."
        ),
        kind="resignation_rejected",
        payload={"notice_id": row.id},
    )
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_resignation.rejected",
        entity_type="employee_resignation_notice",
        entity_id=row.id,
        after_state={
            "employee_id": emp.id,
            "rejection_reason": row.rejection_reason,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_read(row, employee_name=emp.full_name, employee_code=emp.employee_code)
