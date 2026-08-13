"""Payroll routes — salaries, tax slabs, attendance-based net salary compute."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.payroll import (
    PayrollComputeResult,
    PayrollSalaryRow,
    PayrollSalaryUpdate,
    TaxSlabsReplace,
    TaxYearCreate,
    TaxYearRead,
    TaxYearUpdate,
)
from app.services import payroll_service, tax_service
from app.services.payroll_compute import compute_payroll_for_month

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


@router.get("/payroll/compute", response_model=PayrollComputeResult)
def compute_payroll(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("payroll", "read"))],
    period_month: int = Query(..., ge=1, le=12),
    period_year: int = Query(..., ge=2000, le=2100),
    tax_year_id: int = Query(...),
) -> PayrollComputeResult:
    """Net salary = base adjusted by attendance, then monthly tax from selected tax year slabs."""
    return compute_payroll_for_month(
        db,
        period_month=period_month,
        period_year=period_year,
        tax_year_id=tax_year_id,
    )


# --- Tax years / slabs -------------------------------------------------------


@router.get("/payroll/tax-years", response_model=list[TaxYearRead])
def list_tax_years(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("payroll", "read"))],
) -> list[TaxYearRead]:
    return tax_service.list_tax_years(db)


@router.post("/payroll/tax-years", response_model=TaxYearRead, status_code=201)
def create_tax_year(
    payload: TaxYearCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("payroll", "write"))],
) -> TaxYearRead:
    return tax_service.create_tax_year(db, auth, payload)


@router.get("/payroll/tax-years/{tax_year_id}", response_model=TaxYearRead)
def get_tax_year(
    tax_year_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("payroll", "read"))],
) -> TaxYearRead:
    return tax_service.get_tax_year_read(db, tax_year_id)


@router.patch("/payroll/tax-years/{tax_year_id}", response_model=TaxYearRead)
def patch_tax_year(
    tax_year_id: int,
    payload: TaxYearUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("payroll", "write"))],
) -> TaxYearRead:
    return tax_service.update_tax_year(db, auth, tax_year_id, payload)


@router.put("/payroll/tax-years/{tax_year_id}/slabs", response_model=TaxYearRead)
def replace_tax_slabs(
    tax_year_id: int,
    payload: TaxSlabsReplace,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("payroll", "write"))],
) -> TaxYearRead:
    return tax_service.replace_slabs(db, auth, tax_year_id, payload)
