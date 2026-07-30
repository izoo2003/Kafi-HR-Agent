"""CV file intake stub — full logic with FEATURE_CV_SCREENING.md."""
from __future__ import annotations

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
