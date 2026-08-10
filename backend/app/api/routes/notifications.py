"""In-app notifications API."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.schemas.common import AuthContext, MessageResponse, PaginatedResponse
from app.schemas.notification import AppNotificationRead, UnreadCountResponse
from app.services import notification_service as svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedResponse[AppNotificationRead])
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    unread_only: bool = False,
) -> PaginatedResponse[AppNotificationRead]:
    return svc.list_for_user(
        db, auth, page=page, page_size=page_size, unread_only=unread_only
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
) -> UnreadCountResponse:
    return UnreadCountResponse(unread=svc.unread_count(db, auth))


@router.post("/{notification_id}/read", response_model=AppNotificationRead)
def read_notification(
    notification_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
) -> AppNotificationRead:
    return AppNotificationRead.model_validate(svc.mark_read(db, auth, notification_id))


@router.post("/read-all", response_model=MessageResponse)
def read_all(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
) -> MessageResponse:
    n = svc.mark_all_read(db, auth)
    return MessageResponse(message=f"Marked {n} notification(s) read")
