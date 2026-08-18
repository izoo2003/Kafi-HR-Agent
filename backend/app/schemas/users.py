"""User admin schemas — API_ENDPOINTS.md §2."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    login_identifier: str | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class UserSetPassword(BaseModel):
    password: str = Field(min_length=4, max_length=128)


class UserPasswordSetResponse(BaseModel):
    id: int
    full_name: str
    username: str | None
    email: str
    login_identifier: str
    password: str


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
