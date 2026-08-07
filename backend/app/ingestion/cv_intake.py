"""CV file intake stub — full logic with FEATURE_CV_SCREENING.md."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ValidationFailed
from app.models.cv_screening import Candidate

ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}
MAX_BYTES = 10 * 1024 * 1024


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
        raise ValidationFailed("CV must be PDF, DOCX, or TXT")
    if len(content) > MAX_BYTES:
        raise ValidationFailed("CV exceeds 10MB limit")

    settings = get_settings()
    settings.uploads_cvs_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    dest = settings.uploads_cvs_dir / f"jd{job_description_id}_{safe}"
    dest.write_bytes(content)

    candidate = Candidate(
        job_description_id=job_description_id,
        full_name=full_name,
        email=email,
        cv_file_path=str(dest),
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
        raise ValidationFailed(f"CV '{filename}' must be PDF, DOCX, or TXT")
    if len(content) > MAX_BYTES:
        raise ValidationFailed(f"CV '{filename}' exceeds 10MB limit")

    settings = get_settings()
    settings.uploads_cvs_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in filename)
    dest = settings.uploads_cvs_dir / f"{source}_{safe}"
    dest.write_bytes(content)

    candidate = Candidate(
        job_description_id=None,
        full_name=full_name,
        email=email,
        phone=phone,
        cv_file_path=str(dest),
        status="uploaded",
        source=source,
        source_ref=source_ref,
        submitted_at=submitted_at,
    )
    db.add(candidate)
    db.flush()
    return candidate
