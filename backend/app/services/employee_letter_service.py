"""Generate appointment letters and employment contracts for an employee."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BusinessRuleViolation, EntityNotFound, ValidationFailed
from app.core.gemini_client import generate_content_with_fallback
from app.ingestion.employee_docs import delete_stored_file, read_stored_file, store_employee_file, store_letter_file
from app.models.employees import EmployeeDocument
from app.reporting.employee_letters import letter_kinds, render_docx_bytes
from app.schemas.common import AuthContext
from app.schemas.employees import LETTER_CATEGORIES, LETTER_SIGNED_CATEGORIES, LetterSignatureVerifyResult
from app.services import audit_service, employee_service

logger = logging.getLogger(__name__)

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".heif"}

_MISSING = "It is not created yet. Create them first."


def _category(kind: str) -> str:
    if kind not in LETTER_CATEGORIES:
        raise ValidationFailed(f"Unknown letter type '{kind}'")
    return LETTER_CATEGORIES[kind]


def _signed_category(kind: str) -> str:
    if kind not in LETTER_SIGNED_CATEGORIES:
        raise ValidationFailed(f"Unknown letter type '{kind}'")
    return LETTER_SIGNED_CATEGORIES[kind]


def _latest_letter(db: Session, employee_id: int, kind: str) -> EmployeeDocument | None:
    cat = _category(kind)
    return (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.employee_id == employee_id, EmployeeDocument.category == cat)
        .order_by(EmployeeDocument.id.desc())
        .first()
    )


def _delete_category_docs(db: Session, employee_id: int, category: str) -> None:
    existing = (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.employee_id == employee_id, EmployeeDocument.category == category)
        .all()
    )
    for doc in existing:
        path = doc.file_path
        db.delete(doc)
        db.flush()
        delete_stored_file(path)


def generate_letter(
    db: Session,
    auth: AuthContext,
    employee_id: int,
    kind: str,
) -> tuple[bytes, str]:
    employee = employee_service.get_employee(db, employee_id)
    try:
        content, filename = render_docx_bytes(kind, employee)
    except FileNotFoundError as exc:
        raise ValidationFailed(str(exc)) from exc
    except Exception as exc:
        logger.exception("Letter render failed for employee %s kind %s", employee_id, kind)
        raise ValidationFailed(f"Could not generate letter: {exc}") from exc
    cat = _category(kind)
    # Recreate clears prior letter + any signed/verified scan
    _delete_category_docs(db, employee.id, cat)
    _delete_category_docs(db, employee.id, _signed_category(kind))

    stored_path, mime = store_letter_file(
        employee_id=employee.id,
        filename=filename,
        content=content,
    )
    row = EmployeeDocument(
        employee_id=employee.id,
        category=cat,
        title="Appointment letter" if kind == "appointment" else "Employment contract",
        file_path=stored_path,
        original_filename=filename,
        mime_type=mime or DOCX_TYPE,
    )
    db.add(row)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action=f"employee.letter_{kind}",
        entity_type="employee",
        entity_id=employee.id,
        after_state={"filename": filename, "kind": kind, "document_id": row.id},
    )
    return content, filename


def view_stored_letter(db: Session, employee_id: int, kind: str) -> tuple[bytes, str]:
    employee_service.get_employee(db, employee_id)
    if kind not in letter_kinds():
        raise ValidationFailed(f"Unknown letter type '{kind}'")
    doc = _latest_letter(db, employee_id, kind)
    if doc is None:
        raise EntityNotFound(_MISSING)
    return read_stored_file(doc.file_path), doc.original_filename or f"{kind}.docx"


def _parse_vision_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    raise ValidationFailed("Could not parse signature verification response from AI")


def _ai_check_signature(*, image_bytes: bytes, mime_type: str, kind: str) -> dict[str, Any]:
    settings = get_settings()
    api_keys = settings.resolved_gemini_api_keys()
    if not api_keys:
        raise ValidationFailed(
            "Letter signature verification requires GEMINI_API_KEY on the backend."
        )
    letter_label = "appointment letter" if kind == "appointment" else "employment contract"
    prompt = f"""You are verifying a signed HR {letter_label} image for an HR system.

Look only for whether a handwritten / ink / wet signature (or clear signed mark from a person)
appears on the document — typically near a signature line, acknowledgement, or acceptance area.

Return ONLY valid JSON (no markdown) with this exact shape:
{{
  "looks_like_letter_document": true,
  "image_readable": true,
  "has_client_signature": true,
  "notes": "short note or null"
}}

Rules:
- has_client_signature=true only if you can clearly see a human signature or signed mark on the page.
- Printed names, typed text, stamps alone, or blank signature lines do NOT count as a signature.
- If the image is too blurry or cropped to judge, set image_readable=false and has_client_signature=false.
- If this does not look like a letter/contract page at all, set looks_like_letter_document=false.
"""
    response = generate_content_with_fallback(
        api_keys=api_keys,
        models=settings.resolved_gemini_models(),
        prompt=[
            prompt,
            {"mime_type": mime_type or "image/jpeg", "data": image_bytes},
        ],
        pool_id="letter_verify",
    )
    return _parse_vision_json(getattr(response, "text", "") or "")


def verify_letter_signature(
    db: Session,
    auth: AuthContext,
    employee_id: int,
    kind: str,
    *,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> LetterSignatureVerifyResult:
    employee = employee_service.get_employee(db, employee_id)
    if kind not in LETTER_CATEGORIES:
        raise ValidationFailed(f"Unknown letter type '{kind}'")
    if _latest_letter(db, employee_id, kind) is None:
        raise BusinessRuleViolation(_MISSING)

    suffix = ""
    if "." in (filename or ""):
        suffix = "." + filename.rsplit(".", 1)[-1].lower()
    mime = (mime_type or "").lower()
    if not mime.startswith("image/") and suffix not in IMAGE_SUFFIXES:
        raise ValidationFailed(
            "Upload an image of the signed letter (PNG, JPG, WEBP, GIF, or HEIC) — PDF is not accepted."
        )
    if not content:
        raise ValidationFailed("Uploaded image is empty")

    try:
        vision = _ai_check_signature(
            image_bytes=content,
            mime_type=mime if mime.startswith("image/") else "image/jpeg",
            kind=kind,
        )
    except ValidationFailed:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Letter signature AI failed")
        raise ValidationFailed(f"AI signature check failed: {exc}") from exc

    looks_like = bool(vision.get("looks_like_letter_document", True))
    readable = bool(vision.get("image_readable", True))
    has_sig = bool(vision.get("has_client_signature", False))
    notes = str(vision.get("notes") or "").strip() or None

    if not looks_like:
        return LetterSignatureVerifyResult(
            verified=False,
            status="not_letter",
            message=notes
            or "This image does not look like the appointment/contract letter. Upload a clear photo of the signed document.",
            kind=kind,
            employee_id=employee.id,
        )
    if not readable:
        return LetterSignatureVerifyResult(
            verified=False,
            status="unreadable",
            message=notes
            or "The image is too unclear to verify a signature. Retake a sharper photo of the signed page.",
            kind=kind,
            employee_id=employee.id,
        )
    if not has_sig:
        return LetterSignatureVerifyResult(
            verified=False,
            status="no_signature",
            message=notes
            or "No client signature was found on this document. Ask them to sign, then upload again.",
            kind=kind,
            employee_id=employee.id,
        )

    signed_cat = _signed_category(kind)
    _delete_category_docs(db, employee.id, signed_cat)
    path, stored_mime = store_employee_file(
        employee_id=employee.id,
        filename=filename or "signed_letter.jpg",
        content=content,
        subdir="letters",
        images_only=True,
    )
    row = EmployeeDocument(
        employee_id=employee.id,
        category=signed_cat,
        title=(
            "Appointment letter — signed (verified)"
            if kind == "appointment"
            else "Employment contract — signed (verified)"
        ),
        file_path=path,
        original_filename=filename or "signed_letter.jpg",
        mime_type=stored_mime or mime or "image/jpeg",
    )
    db.add(row)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action=f"employee.letter_{kind}_verified",
        entity_type="employee",
        entity_id=employee.id,
        after_state={
            "kind": kind,
            "document_id": row.id,
            "filename": row.original_filename,
            "ai_notes": notes,
        },
    )
    return LetterSignatureVerifyResult(
        verified=True,
        status="verified",
        message="Signature found — letter marked Verified.",
        kind=kind,
        employee_id=employee.id,
        document_id=row.id,
    )
