"""User directory for admin panel."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    EntityNotFound,
    PermissionDenied,
    ValidationFailed,
)
from app.core.security import hash_password
from app.models.employees import Department, Employee
from app.models.identity import Role, User
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.users import UserCreate, UserPasswordSetResponse, UserRead
from app.services import audit_service
from app.services.auth_service import SELF_SERVICE_EMAIL_DOMAIN

_STAFF_ROLES = {
    "super_admin",
    "hr_manager",
    "payroll_officer",
    "department_head",
    "recruiter",
    "readonly_auditor",
}


def _serialize_user(user: User, employee: Employee | None, department: Department | None) -> UserRead:
    email = (user.email or "").lower()
    ident = (user.username or "").strip() or user.email
    return UserRead(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=[r.name for r in user.roles],
        department_id=employee.department_id if employee else None,
        department_name=department.name if department else None,
        linked_employee_id=employee.id if employee else None,
        is_self_registered=email.endswith(f"@{SELF_SERVICE_EMAIL_DOMAIN}") or bool(user.username),
        login_identifier=ident,
        login_pin=user.login_pin,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def _is_staff_account(user: User) -> bool:
    names = {r.name for r in (user.roles or [])}
    return bool(names & _STAFF_ROLES)


def list_users(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
    self_registered_only: bool = False,
) -> PaginatedResponse[UserRead]:
    q = db.query(User).options(joinedload(User.roles))
    # Registered-user admin list hides deactivated logins by default (e.g. after resignation).
    if is_active is not None:
        q = q.filter(User.is_active.is_(is_active))
    elif self_registered_only:
        q = q.filter(User.is_active.is_(True))
    if self_registered_only:
        # Registered user accounts only — hide seeded staff/demo management logins.
        q = q.filter(User.email.like(f"%@{SELF_SERVICE_EMAIL_DOMAIN}"))

    rows = q.order_by(User.created_at.desc(), User.id.desc()).all()
    if self_registered_only:
        rows = [u for u in rows if not _is_staff_account(u)]

    total = len(rows)
    page_rows = rows[(page - 1) * page_size : (page - 1) * page_size + page_size]

    employee_by_user: dict[int, Employee] = {}
    if page_rows:
        user_ids = [u.id for u in page_rows]
        employees = db.query(Employee).filter(Employee.user_id.in_(user_ids)).all()
        employee_by_user = {e.user_id: e for e in employees if e.user_id is not None}

    dept_ids = {e.department_id for e in employee_by_user.values()}
    departments: dict[int, Department] = {}
    if dept_ids:
        departments = {
            d.id: d for d in db.query(Department).filter(Department.id.in_(dept_ids)).all()
        }

    items: list[UserRead] = []
    for user in page_rows:
        employee = employee_by_user.get(user.id)
        department = departments.get(employee.department_id) if employee else None
        items.append(_serialize_user(user, employee, department))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def create_user(db: Session, auth: AuthContext, payload: UserCreate) -> UserRead:
    from app.schemas.auth import RegisterRequest

    cleaned = RegisterRequest(
        full_name=payload.full_name,
        username=payload.username,
        pin=payload.pin,
        department_id=payload.department_id,
    )
    dept = db.query(Department).filter(Department.id == cleaned.department_id).one_or_none()
    if dept is None:
        raise ValidationFailed("department_id does not exist")

    if db.query(User).filter(User.username == cleaned.username).one_or_none():
        raise ConflictError("That username is already taken")

    email = f"{cleaned.username}@{SELF_SERVICE_EMAIL_DOMAIN}"
    if db.query(User).filter(User.email == email).one_or_none():
        raise ConflictError("That username is already taken")

    role = db.query(Role).filter(Role.name == "employee").one_or_none()
    if role is None:
        raise ValidationFailed("Employee role is not seeded")

    user = User(
        email=email,
        username=cleaned.username,
        password_hash=hash_password(cleaned.pin),
        login_pin=cleaned.pin,
        full_name=cleaned.full_name.strip(),
        is_active=True,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()

    employee = Employee(
        user_id=user.id,
        employee_code=f"S{user.id:05d}",
        full_name=user.full_name,
        department_id=dept.id,
        role_title=dept.name or "Employee",
        employment_type="full_time",
        date_joined=date.today(),
        status="active",
        email=email,
    )
    db.add(employee)
    db.flush()

    audit_service.log_from_auth(
        db,
        auth,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        after_state={
            "username": user.username,
            "full_name": user.full_name,
            "department_id": dept.id,
            "employee_id": employee.id,
            "created_by_admin": True,
        },
    )
    return _serialize_user(user, employee, dept)


def set_password(
    db: Session, auth: AuthContext, user_id: int, new_password: str
) -> UserPasswordSetResponse:
    user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).one_or_none()
    if user is None:
        raise EntityNotFound(f"User {user_id} not found")
    user.password_hash = hash_password(new_password)
    user.login_pin = new_password
    db.flush()
    ident = (user.username or "").strip() or user.email
    audit_service.log_from_auth(
        db,
        auth,
        action="user.password_reset",
        entity_type="user",
        entity_id=user.id,
        after_state={"login_identifier": ident},
    )
    return UserPasswordSetResponse(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        login_identifier=ident,
        password=new_password,
    )


def deactivate_user(db: Session, auth: AuthContext, user_id: int) -> UserRead:
    user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).one_or_none()
    if user is None:
        raise EntityNotFound(f"User {user_id} not found")
    if user.id == auth.user_id:
        raise PermissionDenied("You cannot remove your own login")
    if _is_staff_account(user):
        raise BusinessRuleViolation("Staff admin accounts cannot be removed from this list")
    if not user.is_active:
        employee = db.query(Employee).filter(Employee.user_id == user.id).one_or_none()
        dept = (
            db.query(Department).filter(Department.id == employee.department_id).one_or_none()
            if employee
            else None
        )
        return _serialize_user(user, employee, dept)

    user.is_active = False
    employee = db.query(Employee).filter(Employee.user_id == user.id).one_or_none()
    if employee is not None and employee.status != "terminated":
        employee.status = "terminated"
        employee.date_exited = date.today()
    db.flush()
    dept = (
        db.query(Department).filter(Department.id == employee.department_id).one_or_none()
        if employee
        else None
    )
    audit_service.log_from_auth(
        db,
        auth,
        action="user.deactivated",
        entity_type="user",
        entity_id=user.id,
        after_state={
            "username": user.username,
            "employee_id": employee.id if employee else None,
        },
    )
    return _serialize_user(user, employee, dept)
