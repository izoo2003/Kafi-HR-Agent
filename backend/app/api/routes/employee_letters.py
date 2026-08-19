"""Appointment / contract letter downloads — kept off /employees/{id} to avoid 404s."""
from __future__ import annotations

from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext
from app.services import employee_letter_service

router = APIRouter(tags=["employee-letters"])

LetterKind = Literal["appointment", "contract"]


def _letter_response(content: bytes, filename: str) -> Response:
    safe = quote(filename or "letter.docx")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe}"},
    )


@router.get("/employees/{employee_id}/letters/{kind}")
def view_employee_letter(
    employee_id: int,
    kind: LetterKind,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
) -> Response:
    content, filename = employee_letter_service.view_stored_letter(db, employee_id, kind)
    return _letter_response(content, filename)


@router.post("/employees/{employee_id}/letters/{kind}")
def create_employee_letter(
    employee_id: int,
    kind: LetterKind,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> Response:
    content, filename = employee_letter_service.generate_letter(db, auth, employee_id, kind)
    return _letter_response(content, filename)
