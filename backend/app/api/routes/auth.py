"""Auth routes — /api/v1/auth/*."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.common import AuthContext, MessageResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return auth_service.login(db, body.email, body.password, ip_address=_client_ip(request))


@router.post("/login/form", response_model=TokenResponse, include_in_schema=False)
def login_form(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """OAuth2 password form for Swagger Authorize button (username = email)."""
    return auth_service.login(db, form.username, form.password, ip_address=_client_ip(request))


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    return auth_service.refresh_tokens(db, body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
) -> MessageResponse:
    auth_service.logout(db, auth, ip_address=_client_ip(request))
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=AuthContext)
def me(auth: Annotated[AuthContext, Depends(get_current_user)]) -> AuthContext:
    return auth
