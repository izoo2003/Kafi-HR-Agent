"""User directory for admin panel."""
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import EntityNotFound
from app.core.security import hash_password
from app.models.employees import Department, Employee
from app.models.identity import User
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.users import UserPasswordSetResponse, UserRead
from app.services import audit_service
from app.services.auth_service import SELF_SERVICE_EMAIL_DOMAIN


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
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


def list_users(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
    self_registered_only: bool = False,
) -> PaginatedResponse[UserRead]:
    q = db.query(User).options(joinedload(User.roles))
    if is_active is not None:
        q = q.filter(User.is_active.is_(is_active))
    if self_registered_only:
        q = q.filter(User.email.like(f"%@{SELF_SERVICE_EMAIL_DOMAIN}"))

    total = q.count()
    rows = (
        q.order_by(User.created_at.desc(), User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    employee_by_user: dict[int, Employee] = {}
    if rows:
        user_ids = [u.id for u in rows]
        employees = db.query(Employee).filter(Employee.user_id.in_(user_ids)).all()
        employee_by_user = {e.user_id: e for e in employees if e.user_id is not None}

    dept_ids = {e.department_id for e in employee_by_user.values()}
    departments: dict[int, Department] = {}
    if dept_ids:
        departments = {
            d.id: d for d in db.query(Department).filter(Department.id.in_(dept_ids)).all()
        }

    items: list[UserRead] = []
    for user in rows:
        employee = employee_by_user.get(user.id)
        department = departments.get(employee.department_id) if employee else None
        items.append(_serialize_user(user, employee, department))

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def set_password(
    db: Session, auth: AuthContext, user_id: int, new_password: str
) -> UserPasswordSetResponse:
    user = db.query(User).options(joinedload(User.roles)).filter(User.id == user_id).one_or_none()
    if user is None:
        raise EntityNotFound(f"User {user_id} not found")
    user.password_hash = hash_password(new_password)
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
