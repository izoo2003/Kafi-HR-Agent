"""FastAPI dependencies: current user, permission gate, pagination."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import InvalidAuthContext, PermissionDenied
from app.core.security import decode_token
from app.models.employees import Employee
from app.models.identity import AgentAccessMatrix, User
from app.schemas.common import PERMISSION_RANK, AuthContext

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/form", auto_error=True)

AGENT_KEY = "hr_admin"


def _resolve_permissions(db: Session, role_ids: list[int]) -> dict[str, str]:
    """Highest permission level per module across all of the user's roles."""
    if not role_ids:
        return {}
    rows = (
        db.query(AgentAccessMatrix)
        .filter(
            AgentAccessMatrix.role_id.in_(role_ids),
            AgentAccessMatrix.agent_key == AGENT_KEY,
        )
        .all()
    )
    resolved: dict[str, str] = {}
    for row in rows:
        key = f"{row.agent_key}.{row.module_key}"
        current = resolved.get(key, "none")
        if PERMISSION_RANK.get(row.permission, 0) > PERMISSION_RANK.get(current, 0):
            resolved[key] = row.permission
    return resolved


def build_auth_context(db: Session, user: User, *, source: str = "standalone") -> AuthContext:
    role_names = [r.name for r in user.roles]
    role_ids = [r.id for r in user.roles]
    employee = db.query(Employee).filter(Employee.user_id == user.id).one_or_none()
    return AuthContext(
        user_id=user.id,
        email=user.email,
        username=user.username,
        roles=role_names,
        agent_permissions=_resolve_permissions(db, role_ids),
        source=source if source in ("standalone", "orchestrator") else "standalone",
        linked_employee_id=employee.id if employee else None,
        department_id=employee.department_id if employee else None,
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthContext:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise InvalidAuthContext("Access token required")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidAuthContext("Malformed token subject") from exc

    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None or not user.is_active:
        raise InvalidAuthContext("User not found or inactive")

    source = payload.get("source", "standalone")
    return build_auth_context(db, user, source=str(source))


def require_permission(module_key: str, min_level: str):
    """Declarative route gate — checks agent_access_matrix, never hardcodes role names."""

    def _dependency(auth: Annotated[AuthContext, Depends(get_current_user)]) -> AuthContext:
        key = f"{AGENT_KEY}.{module_key}"
        level = auth.agent_permissions.get(key, "none")
        if PERMISSION_RANK.get(level, 0) < PERMISSION_RANK.get(min_level, 99):
            raise PermissionDenied(
                f"Requires {module_key}:{min_level}, have {level}",
                details={"module_key": module_key, "required": min_level, "actual": level},
            )
        return auth

    return _dependency


def pagination_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, int]:
    return {"page": page, "page_size": page_size, "offset": (page - 1) * page_size}
