"""System / integration models — DATABASE_SCHEMA.md §8."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base
from app.models.base import TimestampMixin


class IntegrationRegistry(Base, TimestampMixin):
    __tablename__ = "integration_registry"

    agent_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String, default="standalone", nullable=False)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SystemConfig(Base, TimestampMixin):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
