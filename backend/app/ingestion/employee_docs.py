"""Employee document file intake (PDF / images)."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import ValidationFailed

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".heif"}
PDF_SUFFIXES = {".pdf"}
ALLOWED_SUFFIXES = IMAGE_SUFFIXES | PDF_SUFFIXES
MAX_BYTES = 15 * 1024 * 1024


def _safe_name(filename: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)


def store_employee_file(
    *,
    employee_id: int,
    filename: str,
    content: bytes,
    subdir: str = "documents",
    images_only: bool = False,
) -> tuple[str, str | None]:
    """Persist an uploaded file; returns (absolute_path, mime_type)."""
    raw_name = (filename or "").strip() or "upload.bin"
    suffix = Path(raw_name).suffix.lower()

    # Some mobile browsers omit the extension — infer from MIME later via name guess.
    if not suffix and images_only:
        suffix = ".jpg"
        raw_name = f"{raw_name}.jpg"

    allowed = IMAGE_SUFFIXES if images_only else ALLOWED_SUFFIXES
    if suffix not in allowed:
        if images_only:
            raise ValidationFailed(
                "CNIC / photo uploads must be an image (PNG, JPG, WEBP, GIF, or HEIC) — PDF is not allowed"
            )
        raise ValidationFailed("File must be PDF or an image (PNG, JPG, WEBP, GIF, HEIC)")
    if not content:
        raise ValidationFailed("Uploaded file is empty")
    if len(content) > MAX_BYTES:
        raise ValidationFailed("File exceeds 15MB limit")

    settings = get_settings()
    dest_dir = settings.uploads_employees_dir / f"emp_{employee_id}" / subdir
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe = _safe_name(raw_name)
        dest = dest_dir / f"{uuid4().hex[:10]}_{safe}"
        dest.write_bytes(content)
    except OSError as exc:
        raise ValidationFailed(
            f"Could not store file on server disk ({exc}). "
            "On Railway, ensure the service volume/path for data/uploads is writable."
        ) from exc

    mime, _ = mimetypes.guess_type(raw_name)
    if images_only and not mime:
        mime = "image/jpeg"
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
