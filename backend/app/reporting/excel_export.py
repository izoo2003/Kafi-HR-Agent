"""Excel export helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook


def export_excel(payload: dict, dest: Path) -> Path:
    dest.write_text(f"Excel stub for {payload.get('title', 'report')}\n", encoding="utf-8")
    return dest


def export_ranking_excel(rows: list[dict[str, Any]], dest: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ranking"
    ws.append(["Rank", "Name", "Email", "Score", "Status"])
    for r in rows:
        ws.append([r.get("rank"), r.get("name"), r.get("email"), r.get("score"), r.get("status")])
    wb.save(dest)
    return dest
