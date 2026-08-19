"""Pakistan CNIC document consistency verification.

Important: this is NOT a NADRA government authenticity API.
It validates CNIC number format, reads fields from an uploaded card image
(via Gemini vision when configured), and checks typed CNIC vs OCR.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationFailed
from app.core.gemini_client import generate_content_with_fallback
from app.schemas.cnic import CnicExtractedFields, CnicVerificationChecks, CnicVerificationResult

logger = logging.getLogger(__name__)

CNIC_DIGIT_RE = re.compile(r"^\d{13}$")
CNIC_DISPLAY_RE = re.compile(r"^(\d{5})-(\d{7})-(\d)$")


def normalize_cnic(raw: str) -> str:
    digits = re.sub(r"\D", "", (raw or "").strip())
    return digits


def format_cnic_display(digits: str) -> str:
    d = normalize_cnic(digits)
    if len(d) != 13:
        return d
    return f"{d[:5]}-{d[5:12]}-{d[12]}"


def validate_cnic_format(raw: str) -> tuple[bool, str]:
    digits = normalize_cnic(raw)
    if len(digits) != 13:
        return False, "CNIC must be 13 digits (e.g. 35202-1234567-1)."
    if not CNIC_DIGIT_RE.match(digits):
        return False, "CNIC may only contain digits (dashes/spaces are OK when typing)."
    # Basic structural sanity: first 5 digits are locality code (non-zero overall)
    if digits == "0000000000000":
        return False, "CNIC number is not valid."
    return True, format_cnic_display(digits)


def _parse_gemini_json(text: str) -> dict[str, Any]:
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
    raise ValidationFailed("Could not parse CNIC verification response from vision model")


def _extract_with_gemini(
    *,
    image_bytes: bytes,
    mime_type: str,
    typed_cnic: str,
    settings: Settings,
) -> dict[str, Any]:
    api_keys = settings.resolved_gemini_cnic_api_keys()
    if not api_keys:
        raise ValidationFailed(
            "CNIC image verification requires GEMINI_CNIC_API_KEY or GEMINI_API_KEY on the backend. "
            "Format check alone is available without it."
        )
    prompt = f"""You are verifying a Pakistan NADRA Computerized National Identity Card (CNIC) image for an HR system.

The user typed this CNIC number: {typed_cnic}

Analyze the image and return ONLY valid JSON (no markdown) with this exact shape:
{{
  "looks_like_pakistan_cnic": true,
  "image_readable": true,
  "extracted_cnic": "3520212345671 or null",
  "full_name": "string or null",
  "father_name": "string or null",
  "date_of_birth": "YYYY-MM-DD or null",
  "gender": "male|female|other|null",
  "issue_date": "YYYY-MM-DD or null",
  "expiry_date": "YYYY-MM-DD or null",
  "address": "string or null",
  "notes": "short note if anything looks wrong, else null"
}}

Rules:
- If this is not a Pakistan CNIC / NIC document, set looks_like_pakistan_cnic=false.
- If text is too blurry to read the CNIC number, set image_readable=false and extracted_cnic=null.
- Prefer digits only in extracted_cnic (13 digits). Do not invent fields you cannot see.
- This is document OCR / consistency checking, not a government database lookup.
"""
    response = generate_content_with_fallback(
        api_keys=api_keys,
        models=settings.resolved_gemini_cnic_models(),
        prompt=[
            prompt,
            {"mime_type": mime_type or "image/jpeg", "data": image_bytes},
        ],
        pool_id="cnic",
    )
    return _parse_gemini_json(getattr(response, "text", "") or "")


def verify_cnic(
    *,
    typed_cnic: str,
    image_bytes: bytes | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
    back_image_bytes: bytes | None = None,
    settings: Settings | None = None,
) -> CnicVerificationResult:
    settings = settings or get_settings()
    _ = back_image_bytes  # reserved for future dual-side OCR; front drives match today
    format_ok, format_msg = validate_cnic_format(typed_cnic)
    typed_norm = normalize_cnic(typed_cnic)
    typed_display = format_cnic_display(typed_norm) if format_ok else (typed_cnic or "").strip()

    disclaimer = (
        "This checks CNIC number format and whether the uploaded card image matches the typed "
        "number (AI OCR). It is NOT a NADRA / government authenticity verification."
    )

    if not format_ok:
        return CnicVerificationResult(
            status="invalid_format",
            authentic=False,
            message=format_msg,
            typed_cnic=typed_display,
            extracted=None,
            checks=CnicVerificationChecks(
                format_valid=False,
                image_provided=bool(image_bytes),
                image_readable=False,
                looks_like_pakistan_cnic=False,
                cnic_match=False,
            ),
            disclaimer=disclaimer,
        )

    if not image_bytes:
        return CnicVerificationResult(
            status="needs_image",
            authentic=False,
            message="CNIC format is valid. Upload clear front (and optionally back) CNIC images to complete verification.",
            typed_cnic=typed_display,
            extracted=None,
            checks=CnicVerificationChecks(
                format_valid=True,
                image_provided=False,
                image_readable=False,
                looks_like_pakistan_cnic=False,
                cnic_match=False,
            ),
            disclaimer=disclaimer,
        )

    # Images only — no PDF
    name = (filename or "").lower()
    mt = (mime_type or "").lower()
    if mt == "application/pdf" or name.endswith(".pdf"):
        raise ValidationFailed("CNIC upload must be an image (JPG/PNG/WebP/GIF/HEIC) — PDF is not allowed.")
    if not (mt.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"))):
        raise ValidationFailed("Upload a CNIC image (JPG/PNG/WebP/GIF/HEIC).")

    if len(image_bytes) > 12 * 1024 * 1024:
        raise ValidationFailed("CNIC file is too large (max 12 MB).")

    try:
        vision = _extract_with_gemini(
            image_bytes=image_bytes,
            mime_type=mt if mt.startswith("image/") else "image/jpeg",
            typed_cnic=typed_display,
            settings=settings,
        )
    except ValidationFailed:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("CNIC vision verification failed")
        raise ValidationFailed(f"CNIC image verification failed: {exc}") from exc

    looks_like = bool(vision.get("looks_like_pakistan_cnic"))
    readable = bool(vision.get("image_readable"))
    extracted_cnic_raw = vision.get("extracted_cnic")
    extracted_digits = normalize_cnic(str(extracted_cnic_raw or ""))
    extracted_ok, _ = validate_cnic_format(extracted_digits) if extracted_digits else (False, "")
    match = extracted_ok and extracted_digits == typed_norm

    extracted = CnicExtractedFields(
        cnic=format_cnic_display(extracted_digits) if extracted_ok else None,
        full_name=(str(vision["full_name"]).strip() if vision.get("full_name") else None),
        father_name=(str(vision["father_name"]).strip() if vision.get("father_name") else None),
        date_of_birth=(str(vision["date_of_birth"]).strip() if vision.get("date_of_birth") else None),
        gender=(str(vision["gender"]).strip().lower() if vision.get("gender") else None),
        issue_date=(str(vision["issue_date"]).strip() if vision.get("issue_date") else None),
        expiry_date=(str(vision["expiry_date"]).strip() if vision.get("expiry_date") else None),
        address=(str(vision["address"]).strip() if vision.get("address") else None),
        notes=(str(vision["notes"]).strip() if vision.get("notes") else None),
    )

    checks = CnicVerificationChecks(
        format_valid=True,
        image_provided=True,
        image_readable=readable,
        looks_like_pakistan_cnic=looks_like,
        cnic_match=match,
    )

    if not looks_like:
        return CnicVerificationResult(
            status="not_cnic_document",
            authentic=False,
            message="The uploaded file does not look like a Pakistan CNIC. Please upload a clear front of the card.",
            typed_cnic=typed_display,
            extracted=extracted,
            checks=checks,
            disclaimer=disclaimer,
        )

    if not readable or not extracted_ok:
        return CnicVerificationResult(
            status="unreadable",
            authentic=False,
            message="Could not read the CNIC number from the image. Use a clearer, well-lit photo of the card front.",
            typed_cnic=typed_display,
            extracted=extracted,
            checks=checks,
            disclaimer=disclaimer,
        )

    if not match:
        return CnicVerificationResult(
            status="mismatch",
            authentic=False,
            message=(
                f"Typed CNIC ({typed_display}) does not match the number read from the image "
                f"({format_cnic_display(extracted_digits)}). Check for typos or upload the correct card."
            ),
            typed_cnic=typed_display,
            extracted=extracted,
            checks=checks,
            disclaimer=disclaimer,
        )

    return CnicVerificationResult(
        status="verified",
        authentic=True,
        message="CNIC format is valid and the typed number matches the card image. Details extracted below.",
        typed_cnic=typed_display,
        extracted=extracted,
        checks=checks,
        disclaimer=disclaimer,
    )
