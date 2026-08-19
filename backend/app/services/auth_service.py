"""Auth service — login, register, refresh, me."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import build_auth_context
from app.core.exceptions import InvalidAuthContext, PermissionDenied
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.employees import Department
from app.models.identity import User
from app.schemas.auth import RegisterOptionsDepartment, RegisterOptionsResponse, RegisterRequest, TokenResponse
from app.schemas.common import AuthContext
from app.services import audit_service

SELF_SERVICE_EMAIL_DOMAIN = "self.kafi-hr.local"


def ensure_self_service_schema(db: Session) -> None:
    """create_all will not add columns on existing tables — retrofit username / personal KPIs."""
    bind = db.get_bind()
    if bind is None:
        return
    dialect = bind.dialect.name
    if dialect == "sqlite":
        user_cols = {row[1] for row in db.execute(text("PRAGMA table_info(users)")).fetchall()}
        if user_cols and "username" not in user_cols:
            db.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR"))
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
        if user_cols and "login_pin" not in user_cols:
            db.execute(text("ALTER TABLE users ADD COLUMN login_pin VARCHAR"))
        kpi_cols = {
            row[1] for row in db.execute(text("PRAGMA table_info(kpi_definitions)")).fetchall()
        }
        if kpi_cols and "owner_employee_id" not in kpi_cols:
            db.execute(text("ALTER TABLE kpi_definitions ADD COLUMN owner_employee_id INTEGER"))
            db.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_kpi_definitions_owner_employee_id "
                    "ON kpi_definitions (owner_employee_id)"
                )
            )
        return
    if dialect == "postgresql":
        def _has_column(table: str, column: str) -> bool:
            return (
                db.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
                    ),
                    {"t": table, "c": column},
                ).scalar()
                is not None
            )

        if not _has_column("users", "username"):
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR"))
        db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
        if not _has_column("users", "login_pin"):
            db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS login_pin VARCHAR"))
        if not _has_column("kpi_definitions", "owner_employee_id"):
            db.execute(
                text(
                    "ALTER TABLE kpi_definitions ADD COLUMN IF NOT EXISTS owner_employee_id INTEGER"
                )
            )
        db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_kpi_definitions_owner_employee_id "
                "ON kpi_definitions (owner_employee_id)"
            )
        )


def list_register_options(db: Session) -> RegisterOptionsResponse:
    """Public department list for signup. Seed defaults if the org table is empty."""
    from app.services.seed_service import seed_default_department

    seed_default_department(db)
    rows = db.query(Department).order_by(Department.name).all()
    return RegisterOptionsResponse(
        departments=[RegisterOptionsDepartment(id=d.id, name=d.name) for d in rows]
    )


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    ident = identifier.strip()
    if not ident:
        return None
    by_username = db.query(User).filter(User.username == ident.lower()).one_or_none()
    if by_username is not None:
        return by_username
    return db.query(User).filter(User.email == ident.lower()).one_or_none()


def login(
    db: Session,
    identifier: str,
    password: str,
    *,
    ip_address: str | None = None,
) -> TokenResponse:
    user = _find_user_by_identifier(db, identifier)
    if user is None or not verify_password(password, user.password_hash):
        audit_service.log_action(
            db,
            user_id=user.id if user else None,
            action="auth.login_failed",
            entity_type="user",
            entity_id=user.id if user else None,
            after_state={"identifier": identifier},
            ip_address=ip_address,
        )
        raise InvalidAuthContext("Invalid username or PIN")

    if not user.is_active:
        raise PermissionDenied("User account is deactivated")

    # Keep a plaintext copy so admins can view PINs in Users. Login still verifies password_hash.
    if user.login_pin != password:
        user.login_pin = password[:128]

    return _issue_tokens(db, user, ip_address=ip_address)


def _issue_tokens(db: Session, user: User, *, ip_address: str | None = None) -> TokenResponse:
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


def register(db: Session, payload: RegisterRequest, *, ip_address: str | None = None) -> TokenResponse:
    raise PermissionDenied("Accounts are created by an administrator — ask HR to set up your username and PIN.")


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
