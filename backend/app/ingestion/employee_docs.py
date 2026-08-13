"""Employee document file intake (PDF / images)."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import ValidationFailed

ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_BYTES = 15 * 1024 * 1024


def _safe_name(filename: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)


def store_employee_file(
    *,
    employee_id: int,
    filename: str,
    content: bytes,
    subdir: str = "documents",
) -> tuple[str, str | None]:
    """Persist an uploaded file; returns (absolute_path, mime_type)."""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValidationFailed("File must be PDF or an image (PNG, JPG, WEBP, GIF)")
    if len(content) > MAX_BYTES:
        raise ValidationFailed("File exceeds 15MB limit")

    settings = get_settings()
    dest_dir = settings.uploads_employees_dir / f"emp_{employee_id}" / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_name(filename)
    dest = dest_dir / f"{uuid4().hex[:10]}_{safe}"
    dest.write_bytes(content)
    mime, _ = mimetypes.guess_type(filename)
    return str(dest), mime


def delete_stored_file(file_path: str | None) -> None:
    if not file_path:
        return
    path = Path(file_path)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
