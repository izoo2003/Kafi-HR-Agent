"""Department CRUD service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, EntityNotFound
from app.models.employees import Department
from app.schemas.common import AuthContext
from app.schemas.employees import DepartmentCreate, DepartmentUpdate
from app.services import audit_service


def list_departments(db: Session) -> list[Department]:
    return db.query(Department).order_by(Department.name).all()


def get_department(db: Session, department_id: int) -> Department:
    dept = db.query(Department).filter(Department.id == department_id).one_or_none()
    if dept is None:
        raise EntityNotFound(f"Department {department_id} not found")
    return dept


def create_department(db: Session, auth: AuthContext, payload: DepartmentCreate) -> Department:
    existing = db.query(Department).filter(Department.name == payload.name).one_or_none()
    if existing:
        raise ConflictError(f"Department '{payload.name}' already exists")
    dept = Department(name=payload.name, head_employee_id=payload.head_employee_id)
    db.add(dept)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.created",
        entity_type="department",
        entity_id=dept.id,
        after_state={"name": dept.name},
    )
    return dept


def update_department(
    db: Session, auth: AuthContext, department_id: int, payload: DepartmentUpdate
) -> Department:
    dept = get_department(db, department_id)
    before = {"name": dept.name, "head_employee_id": dept.head_employee_id}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(dept, k, v)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.updated",
        entity_type="department",
        entity_id=dept.id,
        before_state=before,
        after_state=data,
    )
    return dept
