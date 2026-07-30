"""Biometric / attendance file intake stub."""
from __future__ import annotations

from typing import Any


def normalize_biometric_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize CSV/Excel rows into AttendanceRecord-shaped dicts. Feature doc fills rules."""
    return rows
