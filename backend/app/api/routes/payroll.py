"""Payroll routes — salaries for active employees; run generation later."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext, MessageResponse, PaginatedResponse
from app.schemas.payroll import PayrollSalaryRow, PayrollSalaryUpdate
from app.services import payroll_service

router = APIRouter(tags=["payroll"])


@router.get("/payroll/salaries", response_model=PaginatedResponse[PayrollSalaryRow])
def list_payroll_salaries(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("payroll", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[PayrollSalaryRow]:
    return payroll_service.list_active_salaries(db, page=page, page_size=page_size)


@router.patch("/payroll/salaries/{employee_id}", response_model=PayrollSalaryRow)
def update_payroll_salary(
    employee_id: int,
    payload: PayrollSalaryUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("payroll", "write"))],
) -> PayrollSalaryRow:
    return payroll_service.update_employee_salary(db, auth, employee_id, payload)


@router.get("/payroll-runs", response_model=MessageResponse)
def list_payroll_runs(
    _: Annotated[AuthContext, Depends(require_permission("payroll", "read"))],
) -> MessageResponse:
    return MessageResponse(
        message="Payroll runs not implemented yet — use /payroll/salaries for active employee salaries."
    )
