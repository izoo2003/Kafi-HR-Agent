"""Auth service — login, refresh, me."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.deps import build_auth_context
from app.core.exceptions import InvalidAuthContext, PermissionDenied
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.identity import User
from app.schemas.auth import TokenResponse
from app.schemas.common import AuthContext
from app.services import audit_service


def login(db: Session, email: str, password: str, *, ip_address: str | None = None) -> TokenResponse:
    user = db.query(User).filter(User.email == email.lower().strip()).one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        audit_service.log_action(
            db,
            user_id=user.id if user else None,
            action="auth.login_failed",
            entity_type="user",
            entity_id=user.id if user else None,
            after_state={"email": email},
            ip_address=ip_address,
        )
        raise InvalidAuthContext("Invalid email or password")

    if not user.is_active:
        raise PermissionDenied("User account is deactivated")

    user.last_login_at = datetime.now(UTC)
    auth = build_auth_context(db, user, source="standalone")
    access = create_access_token(
        user_id=user.id, email=user.email, roles=auth.roles, source="standalone"
    )
    refresh = create_refresh_token(user_id=user.id, source="standalone")

    audit_service.log_action(
        db,
        user_id=user.id,
        action="auth.login_success",
        entity_type="user",
        entity_id=user.id,
        ip_address=ip_address,
    )
    return TokenResponse(access_token=access, refresh_token=refresh, auth=auth)


def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise InvalidAuthContext("Refresh token required")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidAuthContext("Malformed refresh token") from exc

    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None or not user.is_active:
        raise InvalidAuthContext("User not found or inactive")

    auth = build_auth_context(db, user, source=str(payload.get("source", "standalone")))
    access = create_access_token(
        user_id=user.id, email=user.email, roles=auth.roles, source=auth.source
    )
    new_refresh = create_refresh_token(user_id=user.id, source=auth.source)
    return TokenResponse(access_token=access, refresh_token=new_refresh, auth=auth)


def logout(db: Session, auth: AuthContext, *, ip_address: str | None = None) -> None:
    audit_service.log_action(
        db,
        user_id=auth.user_id,
        action="auth.logout",
        entity_type="user",
        entity_id=auth.user_id,
        ip_address=ip_address,
    )
