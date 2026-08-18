"""Audit logging — every write path should call log_action."""
from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.schemas.common import AuthContext


def _json_safe(value: Any) -> Any:
    """Coerce values SQLAlchemy JSON columns cannot serialize (date, Decimal, …)."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def log_action(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=_json_safe(before_state) if before_state is not None else None,
        after_state=_json_safe(after_state) if after_state is not None else None,
        ip_address=ip_address,
        timestamp=datetime.now(UTC),
    )
    db.add(entry)
    db.flush()

    # Also notify integration seam (local bus stub today).
    from app.integration import interface as integration

    integration.emit_audit_event(
        integration.AuditEvent(
            agent_key="hr_admin",
            action=action,
            entity_type=entity_type or "",
            entity_id=entity_id or 0,
            user_id=user_id or 0,
            timestamp=entry.timestamp,
        )
    )
    return entry


def log_from_auth(
    db: Session,
    auth: AuthContext,
    *,
    action: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    return log_action(
        db,
        user_id=auth.user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        ip_address=ip_address,
    )
