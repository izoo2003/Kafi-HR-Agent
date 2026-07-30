"""Shared Pydantic schemas — AuthContext is the single definition used by API + integration."""
from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

PermissionLevel = Literal["none", "read", "write", "approve", "admin"]
AuthSource = Literal["standalone", "orchestrator"]

PERMISSION_RANK: dict[str, int] = {
    "none": 0,
    "read": 1,
    "write": 2,
    "approve": 3,
    "admin": 4,
}


class AuthContext(BaseModel):
    """Matches INTEGRATION_CONTRACT.md §2 + AUTH_AND_RBAC.md §6 linked_employee_id."""

    user_id: int
    email: str
    roles: list[str]
    agent_permissions: dict[str, str] = Field(default_factory=dict)
    source: AuthSource = "standalone"
    linked_employee_id: int | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class MessageResponse(BaseModel):
    message: str


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
