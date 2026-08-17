"""CNIC verification routes — mounted at /api/v1/cnic (avoids /employees/{id} conflicts)."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.exceptions import ValidationFailed
from app.schemas.cnic import CnicVerificationResult
from app.schemas.common import AuthContext
from app.services import audit_service
from app.services.cnic_verification_service import verify_cnic

router = APIRouter(prefix="/cnic", tags=["cnic"])

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".heif"}


async def _load_image(upload: UploadFile | None, *, label: str) -> tuple[bytes | None, str | None, str | None]:
    if upload is None or not (upload.filename or "").strip():
        return None, None, None
    name = upload.filename or "upload.jpg"
    suffix = Path(name).suffix.lower()
    ctype = (upload.content_type or "").lower()
    if suffix == ".pdf" or "pdf" in ctype:
        raise ValidationFailed(f"{label} must be an image (PNG/JPG/WEBP) — PDF is not allowed")
    if suffix and suffix not in _IMAGE_EXTS and not ctype.startswith("image/"):
        raise ValidationFailed(f"{label} must be an image file")
    if not suffix and ctype.startswith("image/"):
        subtype = ctype.split("/", 1)[-1].split(";")[0].strip()
        ext = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp"}.get(subtype, ".jpg")
        name = f"upload{ext}"
    data = await upload.read()
    if not data:
        raise ValidationFailed(f"{label} file is empty")
    return data, name, ctype or "image/jpeg"


@router.post("/verify", response_model=CnicVerificationResult)
async def verify_cnic_endpoint(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
    typed_cnic: Annotated[str, Form(...)],
    front_image: Annotated[UploadFile | None, File()] = None,
    back_image: Annotated[UploadFile | None, File()] = None,
    image: Annotated[UploadFile | None, File()] = None,
) -> CnicVerificationResult:
    """Format + OCR consistency check. Images only (front required for match; back optional)."""
    front = front_image if front_image and front_image.filename else image
    front_bytes, front_name, front_mime = await _load_image(front, label="Front CNIC image")
    back_bytes, _back_name, _back_mime = await _load_image(back_image, label="Back CNIC image")

    primary_bytes = front_bytes or back_bytes
    primary_name = front_name if front_bytes else _back_name
    primary_mime = front_mime if front_bytes else _back_mime

    result = verify_cnic(
        typed_cnic=typed_cnic,
        image_bytes=primary_bytes,
        filename=primary_name,
        mime_type=primary_mime,
        back_image_bytes=back_bytes if front_bytes and back_bytes else None,
    )
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.cnic_verify",
        entity_type="cnic_verification",
        entity_id=0,
        after_state={
            "status": result.status,
            "authentic": result.authentic,
            "typed_cnic": result.typed_cnic,
            "cnic_match": result.checks.cnic_match,
            "format_valid": result.checks.format_valid,
            "had_front": bool(front_bytes),
            "had_back": bool(back_bytes),
        },
    )
    return result
