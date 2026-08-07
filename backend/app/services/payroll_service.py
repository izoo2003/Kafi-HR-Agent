"""Payroll service — active employee salaries (full run generation later)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolation, EntityNotFound
from app.models.employees import Department, Employee
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.payroll import PayrollSalaryRow, PayrollSalaryUpdate
from app.services import audit_service


def _to_salary_row(db: Session, emp: Employee) -> PayrollSalaryRow:
    dept = db.query(Department).filter(Department.id == emp.department_id).one_or_none()
    return PayrollSalaryRow(
        employee_id=emp.id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        department_id=emp.department_id,
        department_name=dept.name if dept else None,
        role_title=emp.role_title,
        status=emp.status,
        base_salary=emp.base_salary,
        updated_at=emp.updated_at,
    )


def list_active_salaries(
    db: Session, *, page: int = 1, page_size: int = 20
) -> PaginatedResponse[PayrollSalaryRow]:
    q = db.query(Employee).filter(Employee.status == "active")
    total = q.count()
    rows = (
        q.order_by(Employee.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_to_salary_row(db, e) for e in rows]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


def update_employee_salary(
    db: Session, auth: AuthContext, employee_id: int, payload: PayrollSalaryUpdate
) -> PayrollSalaryRow:
    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")
    if emp.status != "active":
        raise BusinessRuleViolation("Salary can only be edited for active employees")

    before = {"base_salary": str(emp.base_salary) if emp.base_salary is not None else None}
    emp.base_salary = payload.base_salary
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="payroll.salary_updated",
        entity_type="employee",
        entity_id=emp.id,
        before_state=before,
        after_state={
            "base_salary": str(emp.base_salary) if emp.base_salary is not None else None
        },
    )
    return _to_salary_row(db, emp)
