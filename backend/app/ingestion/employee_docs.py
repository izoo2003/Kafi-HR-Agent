"""Employee document file intake (PDF / images) — Supabase Storage when configured."""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings
from app.core.exceptions import EntityNotFound, ValidationFailed
from app.core import supabase_storage

logger = logging.getLogger(__name__)

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


def store_letter_file(
    *,
    employee_id: int,
    filename: str,
    content: bytes,
) -> tuple[str, str | None]:
    """Store a generated Word letter (.docx)."""
    raw_name = (filename or "").strip() or "letter.docx"
    suffix = Path(raw_name).suffix.lower()
    if suffix != ".docx":
        raw_name = f"{Path(raw_name).stem}.docx"
        suffix = ".docx"
    if not content:
        raise ValidationFailed("Letter file is empty")
    if len(content) > MAX_BYTES:
        raise ValidationFailed("File exceeds 15MB limit")

    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    settings = get_settings()
    safe = _safe_name(raw_name)
    object_name = f"{uuid4().hex[:10]}_{safe}"
    relative = f"emp_{employee_id}/letters/{object_name}"

    if supabase_storage.storage_configured(settings):
        try:
            uri = supabase_storage.upload_bytes(
                object_path=relative,
                content=content,
                content_type=mime,
                settings=settings,
            )
            return uri, mime
        except Exception as exc:
            logger.warning("Letter Storage upload failed, saving locally: %s", exc)

    dest_dir = settings.uploads_employees_dir / f"emp_{employee_id}" / "letters"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / object_name
        dest.write_bytes(content)
    except OSError as exc:
        raise ValidationFailed(
            f"Could not store letter on server disk ({exc}). "
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


def store_department_file(
    *,
    department_id: int,
    kind: str,
    filename: str,
    content: bytes,
) -> tuple[str, str | None]:
    """Persist a department JD/SOP attachment (PDF or image)."""
    raw_name = (filename or "").strip() or "upload.bin"
    suffix = Path(raw_name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValidationFailed("Attachment must be a PDF or an image (PNG, JPG, WEBP, GIF, or HEIC)")
    if not content:
        raise ValidationFailed("Uploaded file is empty")
    if len(content) > MAX_BYTES:
        raise ValidationFailed("File exceeds 15MB limit")

    mime, _ = mimetypes.guess_type(raw_name)
    if suffix == ".pdf":
        mime = "application/pdf"
    settings = get_settings()
    safe = _safe_name(raw_name)
    object_name = f"{uuid4().hex[:10]}_{safe}"
    folder = "job_description" if kind == "job_description" else "sop"
    relative = f"departments/{department_id}/{folder}/{object_name}"

    if supabase_storage.storage_configured(settings):
        try:
            uri = supabase_storage.upload_bytes(
                object_path=relative,
                content=content,
                content_type=mime,
                settings=settings,
            )
            return uri, mime
        except Exception as exc:
            logger.warning("Department file Storage upload failed, saving locally: %s", exc)

    dest_dir = settings.data_dir / "uploads" / "departments" / f"dept_{department_id}" / folder
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / object_name
        dest.write_bytes(content)
    except OSError as exc:
        raise ValidationFailed(f"Could not store department attachment ({exc}).") from exc
    return str(dest), mime


def store_job_image(
    *,
    job_id: int,
    filename: str,
    content: bytes,
) -> tuple[str, str | None]:
    raw_name = (filename or "").strip() or "image.jpg"
    suffix = Path(raw_name).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        raise ValidationFailed("Job posting attachments must be images (PNG, JPG, WEBP, or GIF)")
    if not content:
        raise ValidationFailed("Uploaded image is empty")
    if len(content) > MAX_BYTES:
        raise ValidationFailed("File exceeds 15MB limit")

    mime = mimetypes.guess_type(raw_name)[0] or "image/jpeg"
    settings = get_settings()
    safe = _safe_name(raw_name)
    object_name = f"{uuid4().hex[:10]}_{safe}"
    relative = f"jobs/{job_id}/images/{object_name}"

    if supabase_storage.storage_configured(settings):
        try:
            uri = supabase_storage.upload_bytes(
                object_path=relative,
                content=content,
                content_type=mime,
                settings=settings,
            )
            return uri, mime
        except Exception as exc:
            logger.warning("Job image Storage upload failed, saving locally: %s", exc)

    dest_dir = settings.data_dir / "uploads" / "jobs" / f"job_{job_id}" / "images"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / object_name
        dest.write_bytes(content)
    except OSError as exc:
        raise ValidationFailed(f"Could not store job image ({exc}).") from exc
    return str(dest), mime


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
