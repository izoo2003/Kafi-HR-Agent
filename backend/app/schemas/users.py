"""User admin schemas — API_ENDPOINTS.md §2."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str | None = None
    full_name: str
    is_active: bool
    roles: list[str] = []
    department_id: int | None = None
    department_name: str | None = None
    linked_employee_id: int | None = None
    is_self_registered: bool = False
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
