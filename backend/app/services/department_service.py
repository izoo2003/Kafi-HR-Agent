"""Department CRUD service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolation, ConflictError, EntityNotFound
from app.models.attendance import AttendanceRule
from app.models.cv_screening import JobDescription
from app.models.employees import Department, Employee
from app.models.kpi import KpiDefinition
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
    dept = Department(
        name=payload.name,
        head_employee_id=payload.head_employee_id,
        job_description_text=payload.job_description_text,
        sops_text=payload.sops_text,
    )
    db.add(dept)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.created",
        entity_type="department",
        entity_id=dept.id,
        after_state={
            "name": dept.name,
            "job_description_text": dept.job_description_text,
            "sops_text": dept.sops_text,
        },
    )
    return dept


def update_department(
    db: Session, auth: AuthContext, department_id: int, payload: DepartmentUpdate
) -> Department:
    dept = get_department(db, department_id)
    before = {
        "name": dept.name,
        "head_employee_id": dept.head_employee_id,
        "job_description_text": dept.job_description_text,
        "sops_text": dept.sops_text,
    }
    data = payload.model_dump(exclude_unset=True)
    new_name = data.get("name")
    if new_name is not None:
        clash = (
            db.query(Department)
            .filter(Department.name == new_name, Department.id != department_id)
            .one_or_none()
        )
        if clash:
            raise ConflictError(f"Department '{new_name}' already exists")
    old_name = dept.name
    for k, v in data.items():
        setattr(dept, k, v)
    if new_name and new_name != old_name:
        db.query(Employee).filter(Employee.department_id == dept.id).update(
            {Employee.role_title: new_name},
            synchronize_session=False,
        )
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


def delete_department(db: Session, auth: AuthContext, department_id: int) -> None:
    dept = get_department(db, department_id)
    employee_count = db.query(Employee).filter(Employee.department_id == department_id).count()
    jd_count = db.query(JobDescription).filter(JobDescription.department_id == department_id).count()
    kpi_count = db.query(KpiDefinition).filter(KpiDefinition.department_id == department_id).count()
    rule_count = (
        db.query(AttendanceRule)
        .filter(AttendanceRule.applies_to_department_id == department_id)
        .count()
    )
    blockers: list[str] = []
    if employee_count:
        blockers.append(f"{employee_count} employee(s)")
    if jd_count:
        blockers.append(f"{jd_count} job description(s)")
    if kpi_count:
        blockers.append(f"{kpi_count} KPI definition(s)")
    if rule_count:
        blockers.append(f"{rule_count} attendance rule(s)")
    if blockers:
        raise BusinessRuleViolation(
            f"Cannot remove department '{dept.name}' while it is still used by "
            + ", ".join(blockers)
            + ". Reassign or remove those records first."
        )
    name = dept.name
    db.delete(dept)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.deleted",
        entity_type="department",
        entity_id=department_id,
        before_state={"name": name},
    )
