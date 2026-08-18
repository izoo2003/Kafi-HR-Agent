"""CV file intake — Supabase Storage when configured, local disk otherwise."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core import supabase_storage
from app.core.config import get_settings
from app.core.exceptions import EntityNotFound, ValidationFailed
from app.ingestion.cv_classifier import CV_EXTENSIONS
from app.models.cv_screening import Candidate

ALLOWED_SUFFIXES = CV_EXTENSIONS
MAX_BYTES = 10 * 1024 * 1024
_TYPE_HINT = "PDF, DOCX, TXT, or an image of a CV (JPG/PNG/WebP)"

CV_MIME = {
    ".pdf": "application/pdf",
    ".txt": "text/plain; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def _safe_name(filename: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in (filename or ""))
    return cleaned or "cv.bin"


def stored_cv_filename(stored: str) -> str:
    name = (stored or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    return name or "cv.bin"


def cv_mime_for(filename: str) -> str:
    return CV_MIME.get(Path(filename).suffix.lower(), "application/octet-stream")


def persist_cv_bytes(*, filename: str, content: bytes, key_prefix: str) -> str:
    """Save CV bytes; returns supabase:// URI or a local path."""
    settings = get_settings()
    safe = _safe_name(filename)
    object_name = f"{uuid4().hex[:10]}_{safe}"
    prefix = "".join(c if c.isalnum() or c in "_-" else "_" for c in (key_prefix or "inbox"))
    relative = f"cvs/{prefix}/{object_name}"
    mime = cv_mime_for(filename).split(";")[0]

    if supabase_storage.storage_configured(settings):
        return supabase_storage.upload_bytes(
            object_path=relative,
            content=content,
            content_type=mime,
            settings=settings,
        )

    dest_dir = settings.uploads_cvs_dir / prefix
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / object_name
    dest.write_bytes(content)
    return str(dest)


def _resolve_local_cv(raw: str) -> Path | None:
    settings = get_settings()
    path = Path(raw)
    if path.is_file():
        return path
    resolved = settings.resolved_path(raw)
    if resolved.is_file():
        return resolved
    name = path.name
    if not name:
        return None
    for folder in (settings.uploads_cvs_dir, settings.cv_files_dir):
        if not folder.exists():
            continue
        direct = folder / name
        if direct.is_file():
            return direct
        matches = list(folder.rglob(name))
        if len(matches) == 1 and matches[0].is_file():
            return matches[0]
    return None


def read_cv_bytes(stored: str) -> bytes:
    """Load CV bytes from Supabase Storage or local disk (including legacy paths)."""
    raw = (stored or "").strip()
    if not raw:
        raise EntityNotFound("Candidate has no CV file")
    if supabase_storage.is_supabase_uri(raw):
        return supabase_storage.download_bytes(raw)
    path = _resolve_local_cv(raw)
    if path is None:
        raise EntityNotFound("CV file is missing — it may have been stored on a previous server")
    return path.read_bytes()


def store_cv_upload(
    db: Session,
    *,
    job_description_id: int,
    filename: str,
    content: bytes,
    full_name: str | None = None,
    email: str | None = None,
) -> Candidate:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValidationFailed(f"CV must be {_TYPE_HINT}")
    if len(content) > MAX_BYTES:
        raise ValidationFailed("CV exceeds 10MB limit")

    stored = persist_cv_bytes(
        filename=filename,
        content=content,
        key_prefix=f"jd{job_description_id}",
    )

    candidate = Candidate(
        job_description_id=job_description_id,
        full_name=full_name,
        email=email,
        cv_file_path=stored,
        status="uploaded",
    )
    db.add(candidate)
    db.flush()
    return candidate


def store_fetched_cv(
    db: Session,
    *,
    source: str,
    source_ref: str,
    filename: str,
    content: bytes,
    full_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    submitted_at: datetime | None = None,
) -> Candidate:
    """Stores a CV fetched from an automated source (Gmail/Google Form) as an
    unassigned Candidate (job_description_id = NULL) — the matcher decides
    where it goes next. Raises ValidationFailed on bad file type/size just
    like a manual upload; caller (sync_cv_sources) should catch per-item so
    one bad CV doesn't fail the whole sync."""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValidationFailed(f"CV '{filename}' must be {_TYPE_HINT}")
    if len(content) > MAX_BYTES:
        raise ValidationFailed(f"CV '{filename}' exceeds 10MB limit")

    stored = persist_cv_bytes(filename=filename, content=content, key_prefix=source or "inbox")

    candidate = Candidate(
        job_description_id=None,
        full_name=full_name,
        email=email,
        phone=phone,
        cv_file_path=stored,
        status="uploaded",
        source=source,
        source_ref=source_ref,
        submitted_at=submitted_at,
    )
    db.add(candidate)
    db.flush()
    return candidate
