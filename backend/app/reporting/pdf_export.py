"""Shared exporters — stubs until reporting features land."""
from __future__ import annotations

from pathlib import Path


def export_pdf(payload: dict, dest: Path) -> Path:
    dest.write_text(f"PDF stub for {payload.get('title', 'report')}\n", encoding="utf-8")
    return dest


def export_word(payload: dict, dest: Path) -> Path:
    dest.write_text(f"Word stub for {payload.get('title', 'report')}\n", encoding="utf-8")
    return dest


def export_excel(payload: dict, dest: Path) -> Path:
    dest.write_text(f"Excel stub for {payload.get('title', 'report')}\n", encoding="utf-8")
    return dest
