"""Employee document file intake (PDF / images) — Supabase Storage when configured."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import EntityNotFound, ValidationFailed
from app.core import supabase_storage

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
    """Persist an uploaded file; returns (storage_uri_or_path, mime_type).

    Prefer Supabase Storage when SUPABASE_URL + SUPABASE_SECRET_KEY are set.
    Falls back to local disk only when Storage is not configured.
    """
    raw_name = (filename or "").strip() or "upload.bin"
    suffix = Path(raw_name).suffix.lower()

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

    mime, _ = mimetypes.guess_type(raw_name)
    if images_only and not mime:
        mime = "image/jpeg"

    settings = get_settings()
    safe = _safe_name(raw_name)
    object_name = f"{uuid4().hex[:10]}_{safe}"
    relative = f"emp_{employee_id}/{subdir.strip('/')}/{object_name}"

    if supabase_storage.storage_configured(settings):
        uri = supabase_storage.upload_bytes(
            object_path=relative,
            content=content,
            content_type=mime,
            settings=settings,
        )
        return uri, mime

    dest_dir = settings.uploads_employees_dir / f"emp_{employee_id}" / subdir
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / object_name
        dest.write_bytes(content)
    except OSError as exc:
        raise ValidationFailed(
            f"Could not store file on server disk ({exc}). "
            "Configure SUPABASE_URL + SUPABASE_SECRET_KEY for cloud Storage, "
            "or ensure data/uploads is writable."
        ) from exc

    return str(dest), mime


def read_stored_file(file_path: str) -> bytes:
    """Load file bytes from Supabase Storage URI or local disk path."""
    if supabase_storage.is_supabase_uri(file_path):
        return supabase_storage.download_bytes(file_path)
    path = Path(file_path)
    if not path.is_file():
        raise EntityNotFound("File not found on disk")
    return path.read_bytes()


def delete_stored_file(file_path: str | None) -> None:
    if not file_path:
        return
    if supabase_storage.is_supabase_uri(file_path):
        supabase_storage.delete_object(file_path)
        return
    path = Path(file_path)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
