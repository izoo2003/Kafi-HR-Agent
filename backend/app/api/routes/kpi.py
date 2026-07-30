"""KPI routes — API_ENDPOINTS.md §8."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext, MessageResponse, PaginatedResponse
from app.schemas.kpi import (
    DepartmentKpiSummary,
    EmployeeKpiSummary,
    KpiDefinitionCreate,
    KpiDefinitionRead,
    KpiDefinitionUpdate,
    KpiEntryCreate,
    KpiEntryRead,
    KpiEntryUpdate,
    MarkPeriodReviewedRequest,
    MarkPeriodReviewedResponse,
)
from app.services import kpi_service as svc

router = APIRouter(tags=["kpi"])


@router.get("/kpi-definitions", response_model=list[KpiDefinitionRead])
def list_kpi_definitions(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
    department_id: int | None = None,
    include_archived: bool = False,
) -> list[KpiDefinitionRead]:
    rows = svc.list_definitions(
        db, department_id=department_id, include_archived=include_archived
    )
    return [KpiDefinitionRead.model_validate(r) for r in rows]


@router.post("/kpi-definitions", response_model=KpiDefinitionRead, status_code=201)
def create_kpi_definition(
    payload: KpiDefinitionCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> KpiDefinitionRead:
    return KpiDefinitionRead.model_validate(svc.create_definition(db, auth, payload))


@router.patch("/kpi-definitions/{definition_id}", response_model=KpiDefinitionRead)
def patch_kpi_definition(
    definition_id: int,
    payload: KpiDefinitionUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> KpiDefinitionRead:
    return KpiDefinitionRead.model_validate(
        svc.update_definition(db, auth, definition_id, payload)
    )


@router.delete("/kpi-definitions/{definition_id}", response_model=MessageResponse)
def delete_kpi_definition(
    definition_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> MessageResponse:
    svc.archive_definition(db, auth, definition_id)
    return MessageResponse(message="KPI definition archived")


@router.get("/kpi-entries", response_model=PaginatedResponse[KpiEntryRead])
def list_kpi_entries(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    employee_id: int | None = None,
    department_id: int | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> PaginatedResponse[KpiEntryRead]:
    return svc.list_entries(
        db,
        page=page,
        page_size=page_size,
        employee_id=employee_id,
        department_id=department_id,
        period_start=period_start,
        period_end=period_end,
    )


@router.post("/kpi-entries", response_model=KpiEntryRead, status_code=201)
def create_kpi_entry(
    payload: KpiEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> KpiEntryRead:
    return KpiEntryRead.model_validate(svc.create_entry(db, auth, payload))


@router.patch("/kpi-entries/{entry_id}", response_model=KpiEntryRead)
def patch_kpi_entry(
    entry_id: int,
    payload: KpiEntryUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> KpiEntryRead:
    return KpiEntryRead.model_validate(svc.update_entry(db, auth, entry_id, payload))


@router.get("/employees/{employee_id}/kpi-summary", response_model=EmployeeKpiSummary)
def employee_kpi_summary(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> EmployeeKpiSummary:
    return svc.employee_kpi_summary(db, employee_id, period_start, period_end)


@router.get("/departments/{department_id}/kpi-summary", response_model=DepartmentKpiSummary)
def department_kpi_summary(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
    period_start: date = Query(...),
    period_end: date = Query(...),
) -> DepartmentKpiSummary:
    return svc.department_kpi_summary(db, department_id, period_start, period_end)


@router.post(
    "/departments/{department_id}/kpi-period-reviewed",
    response_model=MarkPeriodReviewedResponse,
)
def mark_kpi_period_reviewed(
    department_id: int,
    payload: MarkPeriodReviewedRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "approve"))],
) -> MarkPeriodReviewedResponse:
    return svc.mark_period_reviewed(
        db, auth, department_id, payload.period_start, payload.period_end
    )
