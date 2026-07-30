"""Admin audit log — skeleton."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.models.audit import AuditLog
from app.schemas.common import AuthContext, PaginatedResponse
from pydantic import BaseModel, ConfigDict
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    entity_type: str | None
    entity_id: int | None
    timestamp: datetime


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogRead])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("admin_panel", "read"))],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[AuditLogRead]:
    q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[AuditLogRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/dashboard", response_model=dict)
def dashboard(
    _: Annotated[AuthContext, Depends(require_permission("admin_panel", "read"))],
) -> dict:
    return {"status": "ok", "message": "Admin dashboard scaffolded — implement with FEATURE_ADMIN_PANEL.md."}
