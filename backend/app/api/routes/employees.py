"""Employee & department routes — API_ENDPOINTS.md §3."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.employees import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
)
from app.services import department_service, employee_service

router = APIRouter(tags=["employees"])


@router.get("/departments", response_model=list[DepartmentRead])
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
) -> list[DepartmentRead]:
    return [DepartmentRead.model_validate(d) for d in department_service.list_departments(db)]


@router.post("/departments", response_model=DepartmentRead, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> DepartmentRead:
    return DepartmentRead.model_validate(department_service.create_department(db, auth, payload))


@router.patch("/departments/{department_id}", response_model=DepartmentRead)
def patch_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> DepartmentRead:
    return DepartmentRead.model_validate(
        department_service.update_department(db, auth, department_id, payload)
    )


@router.get("/employees", response_model=PaginatedResponse[EmployeeRead])
def list_employees(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: int | None = None,
    status: str | None = None,
) -> PaginatedResponse[EmployeeRead]:
    return employee_service.list_employees(
        db, page=page, page_size=page_size, department_id=department_id, status=status
    )


@router.post("/employees", response_model=EmployeeRead, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeRead:
    return EmployeeRead.model_validate(employee_service.create_employee(db, auth, payload))


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
) -> EmployeeRead:
    return EmployeeRead.model_validate(employee_service.get_employee(db, employee_id))


@router.patch("/employees/{employee_id}", response_model=EmployeeRead)
def patch_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeRead:
    return EmployeeRead.model_validate(
        employee_service.update_employee(db, auth, employee_id, payload)
    )


@router.delete("/employees/{employee_id}", response_model=EmployeeRead)
def delete_employee(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeRead:
    return EmployeeRead.model_validate(employee_service.exit_employee(db, auth, employee_id))
