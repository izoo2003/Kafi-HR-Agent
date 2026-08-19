"""Users & roles routes — API_ENDPOINTS.md §2."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.models.identity import Role
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.users import RoleRead, UserCreate, UserPasswordSetResponse, UserRead, UserSetPassword
from app.services import user_service

router = APIRouter(tags=["users"])


@router.get("/users", response_model=PaginatedResponse[UserRead])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("users", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    is_active: bool | None = None,
    self_registered_only: bool = False,
) -> PaginatedResponse[UserRead]:
    return user_service.list_users(
        db,
        page=page,
        page_size=page_size,
        is_active=is_active,
        self_registered_only=self_registered_only,
    )


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("users", "write"))],
) -> UserRead:
    return user_service.create_user(db, auth, payload)


@router.get("/roles", response_model=list[RoleRead])
def list_roles(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("users", "read"))],
) -> list[RoleRead]:
    return [RoleRead.model_validate(r) for r in db.query(Role).order_by(Role.name).all()]


@router.post("/users/{user_id}/set-password", response_model=UserPasswordSetResponse)
def set_user_password(
    user_id: int,
    payload: UserSetPassword,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("users", "write"))],
) -> UserPasswordSetResponse:
    return user_service.set_password(db, auth, user_id, payload.password)


@router.delete("/users/{user_id}", response_model=UserRead)
def deactivate_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("users", "write"))],
) -> UserRead:
    return user_service.deactivate_user(db, auth, user_id)
