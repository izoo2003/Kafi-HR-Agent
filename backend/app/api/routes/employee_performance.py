"""Employee Development — performance score & AI summary routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext
from app.schemas.employee_performance import (
    EmployeePerformanceAiSummaryRequest,
    EmployeePerformanceAiSummaryResponse,
    EmployeePerformanceRead,
)
from app.services import employee_performance_service as svc

router = APIRouter(tags=["employee-performance"])


@router.get("/employee-performance", response_model=EmployeePerformanceRead)
def get_employee_performance(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
    employee_id: int = Query(..., ge=1),
    period_year: int = Query(..., ge=2000, le=2100),
    period_month: int = Query(..., ge=1, le=12),
) -> EmployeePerformanceRead:
    return svc.get_employee_performance(
        db,
        auth,
        employee_id=employee_id,
        period_year=period_year,
        period_month=period_month,
    )


@router.post(
    "/employee-performance/ai-summary",
    response_model=EmployeePerformanceAiSummaryResponse,
)
def generate_employee_performance_ai_summary(
    payload: EmployeePerformanceAiSummaryRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> EmployeePerformanceAiSummaryResponse:
    return svc.generate_performance_ai_summary(
        db,
        auth,
        employee_id=payload.employee_id,
        period_year=payload.period_year,
        period_month=payload.period_month,
        settings=get_settings(),
    )
