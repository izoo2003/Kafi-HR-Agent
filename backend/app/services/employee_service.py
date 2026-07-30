"""Employee CRUD service."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, EntityNotFound, ValidationFailed
from app.models.employees import Department, Employee
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.employees import EmployeeCreate, EmployeeRead, EmployeeUpdate
from app.services import audit_service


def list_employees(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    department_id: int | None = None,
    status: str | None = None,
) -> PaginatedResponse[EmployeeRead]:
    q = db.query(Employee)
    if department_id is not None:
        q = q.filter(Employee.department_id == department_id)
    if status is not None:
        q = q.filter(Employee.status == status)
    total = q.count()
    rows = (
        q.order_by(Employee.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=[EmployeeRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")
    return emp


def create_employee(db: Session, auth: AuthContext, payload: EmployeeCreate) -> Employee:
    if db.query(Department).filter(Department.id == payload.department_id).one_or_none() is None:
        raise ValidationFailed("department_id does not exist")
    if db.query(Employee).filter(Employee.employee_code == payload.employee_code).one_or_none():
        raise ConflictError(f"employee_code '{payload.employee_code}' already exists")
    emp = Employee(**payload.model_dump())
    db.add(emp)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.created",
        entity_type="employee",
        entity_id=emp.id,
        after_state={"employee_code": emp.employee_code, "full_name": emp.full_name},
    )
    return emp


def update_employee(
    db: Session, auth: AuthContext, employee_id: int, payload: EmployeeUpdate
) -> Employee:
    emp = get_employee(db, employee_id)
    before = {"full_name": emp.full_name, "status": emp.status, "department_id": emp.department_id}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(emp, k, v)
    db.flush()
    after = {
        k: str(v) if isinstance(v, Decimal) else v for k, v in data.items()
    }
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.updated",
        entity_type="employee",
        entity_id=emp.id,
        before_state=before,
        after_state=after,
    )
    return emp


def exit_employee(db: Session, auth: AuthContext, employee_id: int) -> Employee:
    emp = get_employee(db, employee_id)
    before = {"status": emp.status, "date_exited": str(emp.date_exited) if emp.date_exited else None}
    emp.status = "terminated"
    emp.date_exited = date.today()
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.exited",
        entity_type="employee",
        entity_id=emp.id,
        before_state=before,
        after_state={"status": emp.status, "date_exited": str(emp.date_exited)},
    )
    return emp
