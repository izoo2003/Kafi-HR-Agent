"""Employee Development — resignation letter routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext, MessageResponse
from app.schemas.employee_resignation import (
    EmployeeResignationCreateRequest,
    EmployeeResignationGenerateRequest,
    EmployeeResignationGenerateResponse,
    EmployeeResignationListResponse,
    EmployeeResignationRead,
    EmployeeResignationUpdateRequest,
)
from app.services import employee_resignation_service as svc

router = APIRouter(tags=["employee-resignation"])


@router.post(
    "/employee-resignations/generate",
    response_model=EmployeeResignationGenerateResponse,
)
def generate_resignation(
    payload: EmployeeResignationGenerateRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> EmployeeResignationGenerateResponse:
    return svc.generate_resignation_letter(
        db,
        auth,
        employee_id=payload.employee_id,
        reason=payload.reason,
        effective_date=payload.effective_date,
        settings=get_settings(),
    )


@router.get("/employee-resignations", response_model=EmployeeResignationListResponse)
def list_resignations(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
    employee_id: int | None = Query(None, ge=1),
) -> EmployeeResignationListResponse:
    return svc.list_resignation_notices(db, auth, employee_id=employee_id)


@router.post(
    "/employee-resignations",
    response_model=EmployeeResignationRead,
    status_code=201,
)
def create_resignation(
    payload: EmployeeResignationCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> EmployeeResignationRead:
    return svc.create_resignation_notice(db, auth, payload)


@router.get(
    "/employee-resignations/{notice_id}",
    response_model=EmployeeResignationRead,
)
def get_resignation(
    notice_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
) -> EmployeeResignationRead:
    return svc.get_resignation_notice(db, auth, notice_id)


@router.patch(
    "/employee-resignations/{notice_id}",
    response_model=EmployeeResignationRead,
)
def patch_resignation(
    notice_id: int,
    payload: EmployeeResignationUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> EmployeeResignationRead:
    return svc.update_resignation_notice(db, auth, notice_id, payload)


@router.delete(
    "/employee-resignations/{notice_id}",
    response_model=MessageResponse,
)
def delete_resignation(
    notice_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> MessageResponse:
    svc.delete_resignation_notice(db, auth, notice_id)
    return MessageResponse(message="Resignation notice deleted")


@router.post(
    "/employee-resignations/{notice_id}/accept",
    response_model=EmployeeResignationRead,
)
def accept_resignation(
    notice_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
) -> EmployeeResignationRead:
    """Self-service employees accept their own pending notice (ends employment + login)."""
    return svc.accept_resignation_notice(db, auth, notice_id)
