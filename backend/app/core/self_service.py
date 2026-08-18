"""Employee self-service helpers — AUTH_AND_RBAC.md §6.

Self-service callers are identified by having a linked employee record and
*no* employees-module read access (the seeded `employee` role). Management
roles keep directory access, so they are not row-filtered this way.
"""
from __future__ import annotations

from app.core.exceptions import PermissionDenied
from app.schemas.common import PERMISSION_RANK, AuthContext


def is_self_service(auth: AuthContext) -> bool:
    if auth.linked_employee_id is None:
        return False
    level = auth.agent_permissions.get("hr_admin.employees", "none")
    return PERMISSION_RANK.get(level, 0) < PERMISSION_RANK["read"]


def own_employee_id(auth: AuthContext) -> int | None:
    if is_self_service(auth):
        return auth.linked_employee_id
    return None


def enforce_own_employee(auth: AuthContext, employee_id: int) -> int:
    """Return the employee_id the caller may access (forced to self when applicable)."""
    own = own_employee_id(auth)
    if own is None:
        return employee_id
    if employee_id != own:
        raise PermissionDenied("You can only access your own records")
    return own
