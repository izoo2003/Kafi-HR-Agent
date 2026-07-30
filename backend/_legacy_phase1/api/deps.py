"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Iterator

from sqlalchemy.orm import Session

from app.db.database import get_session


def get_db() -> Iterator[Session]:
    with get_session() as session:
        yield session
