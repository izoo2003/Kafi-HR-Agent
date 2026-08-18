"""Payroll service — active employee salaries (full run generation later)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolation, EntityNotFound
from app.models.employees import Department, Employee
from app.models.payroll import PayrollSheetAdjustment
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.payroll import (
    PayrollSalaryRow,
    PayrollSalaryUpdate,
    PayrollSheetAdjustmentsSave,
)
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


def save_sheet_adjustments(
    db: Session, auth: AuthContext, payload: PayrollSheetAdjustmentsSave
) -> int:
    """Upsert monthly salary-sheet extras and optionally update base salary."""
    saved = 0
    for item in payload.items:
        emp = db.query(Employee).filter(Employee.id == item.employee_id).one_or_none()
        if emp is None:
            raise EntityNotFound(f"Employee {item.employee_id} not found")
        if emp.status != "active":
            raise BusinessRuleViolation("Salary sheet can only be edited for active employees")

        if item.base_salary is not None and emp.base_salary != item.base_salary:
            before = {"base_salary": str(emp.base_salary) if emp.base_salary is not None else None}
            emp.base_salary = item.base_salary
            audit_service.log_from_auth(
                db,
                auth,
                action="payroll.salary_updated",
                entity_type="employee",
                entity_id=emp.id,
                before_state=before,
                after_state={"base_salary": str(emp.base_salary)},
            )

        row = (
            db.query(PayrollSheetAdjustment)
            .filter(
                PayrollSheetAdjustment.employee_id == item.employee_id,
                PayrollSheetAdjustment.period_month == payload.period_month,
                PayrollSheetAdjustment.period_year == payload.period_year,
            )
            .one_or_none()
        )
        before_adj = None
        if row is None:
            row = PayrollSheetAdjustment(
                employee_id=item.employee_id,
                period_month=payload.period_month,
                period_year=payload.period_year,
            )
            db.add(row)
        else:
            before_adj = {
                "allowance_amount": str(row.allowance_amount),
                "loan_deduction_amount": str(row.loan_deduction_amount),
                "advance_amount": str(row.advance_amount),
                "payment_mode": row.payment_mode,
                "remarks": row.remarks,
            }
        row.allowance_amount = item.allowance_amount or Decimal("0")
        row.loan_deduction_amount = item.loan_deduction_amount or Decimal("0")
        row.advance_amount = item.advance_amount or Decimal("0")
        row.payment_mode = (item.payment_mode or "IBFT").strip() or "IBFT"
        row.remarks = item.remarks
        row.days_present = item.days_present
        row.days_absent = item.days_absent
        row.days_late = item.days_late
        row.days_half_day = item.days_half_day
        row.overtime_bonus_days = item.overtime_bonus_days
        row.monthly_tax_override = item.monthly_tax_override
        audit_service.log_from_auth(
            db,
            auth,
            action="payroll.sheet_adjusted",
            entity_type="payroll_sheet_adjustment",
            entity_id=emp.id,
            before_state=before_adj,
            after_state={
                "period_month": payload.period_month,
                "period_year": payload.period_year,
                "allowance_amount": str(row.allowance_amount),
                "loan_deduction_amount": str(row.loan_deduction_amount),
                "advance_amount": str(row.advance_amount),
                "payment_mode": row.payment_mode,
                "remarks": row.remarks,
                "days_present": row.days_present,
                "days_absent": row.days_absent,
                "days_late": row.days_late,
                "days_half_day": row.days_half_day,
                "overtime_bonus_days": row.overtime_bonus_days,
                "monthly_tax_override": (
                    str(row.monthly_tax_override) if row.monthly_tax_override is not None else None
                ),
            },
        )
        saved += 1
    db.flush()
    return saved
