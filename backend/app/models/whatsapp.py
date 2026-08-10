"""WhatsApp inbound message queue — FEATURE_CV_SCREENING.md §11."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin


class WhatsAppInboundMessage(Base, TimestampMixin):
    __tablename__ = "whatsapp_inbound_messages"

    wa_message_id: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    from_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    media_id: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
