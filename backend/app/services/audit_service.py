"""Audit logging — every write path should call log_action."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.schemas.common import AuthContext


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
        before_state=before_state,
        after_state=after_state,
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
