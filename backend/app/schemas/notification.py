"""Notification Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AppNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    body: str
    kind: str
    payload: dict[str, Any] | None
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UnreadCountResponse(BaseModel):
    unread: int
