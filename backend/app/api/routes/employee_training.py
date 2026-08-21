"""Employee Development — training recommend / assign / Things To Learn."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext
from app.schemas.employee_training import (
    EmployeeTrainingAssignRequest,
    EmployeeTrainingAssignResponse,
    EmployeeTrainingAssignmentRead,
    EmployeeTrainingListResponse,
    EmployeeTrainingRecommendRequest,
    EmployeeTrainingRecommendResponse,
    EmployeeTrainingStatusUpdate,
)
from app.services import employee_training_service as svc

router = APIRouter(tags=["employee-training"])


@router.post(
    "/employee-training/recommend",
    response_model=EmployeeTrainingRecommendResponse,
)
def recommend_employee_training(
    payload: EmployeeTrainingRecommendRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> EmployeeTrainingRecommendResponse:
    return svc.recommend_courses(
        db,
        auth,
        employee_id=payload.employee_id,
        topic=payload.topic,
        settings=get_settings(),
    )


@router.post(
    "/employee-training/assign",
    response_model=EmployeeTrainingAssignResponse,
)
def assign_employee_training(
    payload: EmployeeTrainingAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "write"))],
) -> EmployeeTrainingAssignResponse:
    return svc.assign_courses(
        db,
        auth,
        employee_id=payload.employee_id,
        topic=payload.topic,
        courses=payload.courses,
    )


@router.get("/employee-training", response_model=EmployeeTrainingListResponse)
def list_employee_training(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
    employee_id: int | None = Query(None, ge=1),
) -> EmployeeTrainingListResponse:
    return svc.list_assignments(db, auth, employee_id=employee_id)


@router.patch(
    "/employee-training/{assignment_id}",
    response_model=EmployeeTrainingAssignmentRead,
)
def update_employee_training_status(
    assignment_id: int,
    payload: EmployeeTrainingStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("kpi", "read"))],
) -> EmployeeTrainingAssignmentRead:
    return svc.update_assignment_status(
        db,
        auth,
        assignment_id=assignment_id,
        status=payload.status,
    )
