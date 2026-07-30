"""Users & roles routes — skeleton; full CRUD in later feature work."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.models.identity import Role, User
from app.schemas.common import AuthContext, PaginatedResponse
from pydantic import BaseModel, ConfigDict

router = APIRouter(tags=["users"])


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    is_active: bool


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None


@router.get("/users", response_model=PaginatedResponse[UserRead])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("users", "read"))],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[UserRead]:
    q = db.query(User)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[UserRead.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("users", "read"))],
) -> list[RoleRead]:
    return [RoleRead.model_validate(r) for r in db.query(Role).order_by(Role.name).all()]
