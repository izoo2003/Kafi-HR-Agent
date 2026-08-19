"""Generate appointment letters and employment contracts for an employee."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFound, ValidationFailed
from app.ingestion.employee_docs import delete_stored_file, read_stored_file, store_letter_file
from app.models.employees import EmployeeDocument
from app.reporting.employee_letters import letter_kinds, render_docx_bytes
from app.schemas.common import AuthContext
from app.schemas.employees import LETTER_CATEGORIES
from app.services import audit_service, employee_service

logger = logging.getLogger(__name__)

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_MISSING = "It is not created yet. Create them first."


def _category(kind: str) -> str:
    if kind not in LETTER_CATEGORIES:
        raise ValidationFailed(f"Unknown letter type '{kind}'")
    return LETTER_CATEGORIES[kind]


def _latest_letter(db: Session, employee_id: int, kind: str) -> EmployeeDocument | None:
    cat = _category(kind)
    return (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.employee_id == employee_id, EmployeeDocument.category == cat)
        .order_by(EmployeeDocument.id.desc())
        .first()
    )


def generate_letter(
    db: Session,
    auth: AuthContext,
    employee_id: int,
    kind: str,
) -> tuple[bytes, str]:
    employee = employee_service.get_employee(db, employee_id)
    try:
        content, filename = render_docx_bytes(kind, employee)
    except FileNotFoundError as exc:
        raise ValidationFailed(str(exc)) from exc
    except Exception as exc:
        logger.exception("Letter render failed for employee %s kind %s", employee_id, kind)
        raise ValidationFailed(f"Could not generate letter: {exc}") from exc
    cat = _category(kind)
    existing = (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.employee_id == employee.id, EmployeeDocument.category == cat)
        .all()
    )
    for doc in existing:
        path = doc.file_path
        db.delete(doc)
        db.flush()
        delete_stored_file(path)

    stored_path, mime = store_letter_file(
        employee_id=employee.id,
        filename=filename,
        content=content,
    )
    row = EmployeeDocument(
        employee_id=employee.id,
        category=cat,
        title="Appointment letter" if kind == "appointment" else "Employment contract",
        file_path=stored_path,
        original_filename=filename,
        mime_type=mime or DOCX_TYPE,
    )
    db.add(row)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action=f"employee.letter_{kind}",
        entity_type="employee",
        entity_id=employee.id,
        after_state={"filename": filename, "kind": kind, "document_id": row.id},
    )
    return content, filename


def view_stored_letter(db: Session, employee_id: int, kind: str) -> tuple[bytes, str]:
    employee_service.get_employee(db, employee_id)
    if kind not in letter_kinds():
        raise ValidationFailed(f"Unknown letter type '{kind}'")
    doc = _latest_letter(db, employee_id, kind)
    if doc is None:
        raise EntityNotFound(_MISSING)
    return read_stored_file(doc.file_path), doc.original_filename or f"{kind}.docx"
