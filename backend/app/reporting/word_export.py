"""Word export stub."""
from __future__ import annotations

from pathlib import Path


def export_word(payload: dict, dest: Path) -> Path:
    dest.write_text(f"Word stub for {payload.get('title', 'report')}\n", encoding="utf-8")
    return dest
