"""Education marks sheet / grade sheet verification via AI vision + institution lookup.

Important: this is NOT an official board or university registry check.
It reads uploaded documents and uses AI (with optional web search grounding)
to assess whether named schools/colleges/universities appear to be real institutions.
"""
from __future__ import annotations

import io
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.core.exceptions import ValidationFailed
from app.core.gemini_client import generate_content_with_fallback
from app.schemas.education_verification import (
    EducationDocumentSummary,
    EducationInstitutionCheck,
    EducationVerificationChecks,
    EducationVerificationResult,
)

logger = logging.getLogger(__name__)

_MAX_BYTES = 12 * 1024 * 1024
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".heic", ".heif"}


@dataclass
class _UploadedDoc:
    label: str
    filename: str
    mime_type: str
    data: bytes
    is_pdf: bool


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
    raise ValidationFailed("Could not parse education verification response from AI model")


def _extract_pdf_text(data: bytes) -> str:
    import pdfplumber

    parts: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages[:10]:
            text = page.extract_text() or ""
            if text.strip():
                parts.append(text.strip())
    return "\n\n".join(parts)


def _mime_for_image(filename: str, mime_type: str) -> str:
    mt = (mime_type or "").lower()
    if mt.startswith("image/"):
        return mt
    suffix = Path(filename).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".heic": "image/heic",
        ".heif": "image/heif",
    }.get(suffix, "image/jpeg")


def _prepare_doc(
    *,
    data: bytes | None,
    filename: str | None,
    mime_type: str | None,
    label: str,
) -> _UploadedDoc | None:
    if not data:
        return None
    name = (filename or f"{label}.bin").strip()
    suffix = Path(name).suffix.lower()
    ctype = (mime_type or "").lower()
    is_pdf = suffix == ".pdf" or "pdf" in ctype
    if not is_pdf and suffix not in _IMAGE_EXTS and not ctype.startswith("image/"):
        raise ValidationFailed(
            f"{label} must be a PDF or image (PNG/JPG/WEBP/GIF/HEIC)."
        )
    if len(data) > _MAX_BYTES:
        raise ValidationFailed(f"{label} is too large (max 12 MB).")
    return _UploadedDoc(
        label=label,
        filename=name,
        mime_type=ctype or ("application/pdf" if is_pdf else _mime_for_image(name, "")),
        data=data,
        is_pdf=is_pdf,
    )


def _build_extraction_prompt(docs: list[_UploadedDoc]) -> list[Any]:
    prompt = """You are verifying education documents (marks sheets, grade sheets, transcripts) for an HR system.

Analyze every uploaded document and return ONLY valid JSON (no markdown) with this exact shape:
{
  "documents": [
    {
      "label": "marks_sheet or grade_sheet",
      "document_type": "marks_sheet|grade_sheet|unknown",
      "readable": true,
      "looks_like_education_document": true,
      "student_name": "string or null",
      "program_or_degree": "string or null",
      "board_or_university": "string or null",
      "notes": "short note if anything looks wrong, else null"
    }
  ],
  "institutions": [
    {
      "name": "Full official institution name as printed on the document",
      "institution_type": "school|college|university|board|other",
      "country": "string or null",
      "city": "string or null"
    }
  ]
}

Rules:
- List each distinct school, college, university, or examination board mentioned on the documents.
- Use the full printed name (e.g. "University of Karachi", not abbreviations only).
- If text is too blurry or the file is not an education document, set readable=false / looks_like_education_document=false.
- Do not invent institutions not visible on the documents.
- This step is OCR/extraction only — do not verify existence yet.
"""
    parts: list[Any] = [prompt]
    for doc in docs:
        parts.append(f"\n--- Document: {doc.label} ({doc.filename}) ---\n")
        if doc.is_pdf:
            text = _extract_pdf_text(doc.data)
            if text.strip():
                parts.append(f"Extracted PDF text:\n{text[:12000]}")
            else:
                parts.append(
                    "PDF text could not be extracted; treat as unreadable unless you can infer from filename."
                )
        else:
            parts.append(
                {
                    "mime_type": _mime_for_image(doc.filename, doc.mime_type),
                    "data": doc.data,
                }
            )
    return parts


def _build_institution_verification_prompt(institutions: list[dict[str, Any]]) -> str:
    names_block = json.dumps(institutions, ensure_ascii=False, indent=2)
    return f"""You are verifying whether educational institutions exist as real places for an HR system.

For each institution below, use your knowledge and Google Search (when available) to determine
whether it is a real, operating school, college, university, or examination board.

Institutions to verify:
{names_block}

Return ONLY valid JSON (no markdown) with this exact shape:
{{
  "institutions": [
    {{
      "name": "same name as input",
      "institution_type": "school|college|university|board|other",
      "country": "string or null",
      "city": "string or null",
      "verified": true,
      "confidence": "high|medium|low",
      "verification_note": "One sentence: e.g. This university exists and is a recognized public institution in Pakistan.",
      "source_hint": "Brief hint e.g. official website, HEC listing, well-known public university"
    }}
  ]
}}

Rules:
- verified=true only when you are confident the institution is real (not a fabricated or typo name).
- If the name is ambiguous or you cannot confirm it exists, set verified=false and confidence=low.
- Prefer high confidence only for well-documented public institutions.
- This is plausibility / existence checking — NOT verification that the student attended or that grades are authentic.
"""


def _generate_with_optional_search(
    *,
    api_keys: list[str],
    models: list[str],
    prompt: str | list[Any],
    pool_id: str,
    use_search: bool,
) -> Any:
    if use_search:
        import google.generativeai as genai

        last_exc: Exception | None = None
        for key in api_keys:
            genai.configure(api_key=key)
            for model_name in models:
                try:
                    model = genai.GenerativeModel(
                        model_name,
                        tools="google_search_retrieval",
                    )
                    return model.generate_content(prompt)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    logger.info(
                        "Education search grounding failed on %s, will fall back: %s",
                        model_name,
                        exc,
                    )
        if last_exc:
            logger.warning("Search grounding unavailable; using standard Gemini fallback")
    return generate_content_with_fallback(
        api_keys=api_keys,
        models=models,
        prompt=prompt,
        pool_id=pool_id,
    )


def _extract_documents(
    docs: list[_UploadedDoc],
    settings: Settings,
) -> dict[str, Any]:
    api_keys = settings.resolved_gemini_education_api_keys()
    if not api_keys:
        raise ValidationFailed(
            "Education document verification requires GEMINI_EDUCATION_API_KEY "
            "(or GEMINI_API_KEY as fallback) on the backend."
        )
    response = generate_content_with_fallback(
        api_keys=api_keys,
        models=settings.resolved_gemini_education_models(),
        prompt=_build_extraction_prompt(docs),
        pool_id="education_extract",
    )
    return _parse_gemini_json(getattr(response, "text", "") or "")


def _verify_institutions(
    institutions: list[dict[str, Any]],
    settings: Settings,
) -> dict[str, Any]:
    if not institutions:
        return {"institutions": []}
    api_keys = settings.resolved_gemini_education_api_keys()
    prompt = _build_institution_verification_prompt(institutions)
    response = _generate_with_optional_search(
        api_keys=api_keys,
        models=settings.resolved_gemini_education_models(),
        prompt=prompt,
        pool_id="education_verify",
        use_search=True,
    )
    return _parse_gemini_json(getattr(response, "text", "") or "")


def verify_education_documents(
    *,
    uploads: list[tuple[bytes, str, str | None]] | None = None,
    settings: Settings | None = None,
) -> EducationVerificationResult:
    settings = settings or get_settings()
    disclaimer = (
        "This uses AI to read your education documents and check whether named schools, "
        "colleges, or universities appear to be real institutions. It is NOT an official board, "
        "university, or HEC registry verification and does not prove the document is authentic "
        "or that grades were issued by that institution."
    )

    docs: list[_UploadedDoc] = []
    for index, (data, filename, mime_type) in enumerate(uploads or [], start=1):
        prepared = _prepare_doc(
            data=data,
            filename=filename,
            mime_type=mime_type,
            label=f"document_{index}",
        )
        if prepared is not None:
            docs.append(prepared)

    if not docs:
        return EducationVerificationResult(
            status="needs_documents",
            verified=False,
            message="Upload at least one education document (PDF or image) to verify.",
            documents=[],
            institutions=[],
            checks=EducationVerificationChecks(),
            disclaimer=disclaimer,
        )

    try:
        extracted = _extract_documents(docs, settings)
    except ValidationFailed:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Education document extraction failed")
        raise ValidationFailed(f"Education document verification failed: {exc}") from exc

    doc_summaries: list[EducationDocumentSummary] = []
    raw_docs = extracted.get("documents") or []
    if isinstance(raw_docs, list):
        for i, item in enumerate(raw_docs):
            if not isinstance(item, dict):
                continue
            doc_type = str(item.get("document_type") or "unknown").lower()
            if doc_type not in ("marks_sheet", "grade_sheet", "unknown"):
                doc_type = "unknown"
            doc_summaries.append(
                EducationDocumentSummary(
                    document_type=doc_type,  # type: ignore[arg-type]
                    readable=bool(item.get("readable")),
                    looks_like_education_document=bool(
                        item.get("looks_like_education_document")
                    ),
                    student_name=(
                        str(item["student_name"]).strip()
                        if item.get("student_name")
                        else None
                    ),
                    program_or_degree=(
                        str(item["program_or_degree"]).strip()
                        if item.get("program_or_degree")
                        else None
                    ),
                    board_or_university=(
                        str(item["board_or_university"]).strip()
                        if item.get("board_or_university")
                        else None
                    ),
                    notes=(str(item["notes"]).strip() if item.get("notes") else None),
                )
            )
    if not doc_summaries and docs:
        doc_summaries = [
            EducationDocumentSummary(
                document_type="unknown",
                readable=False,
                looks_like_education_document=False,
            )
            for _d in docs
        ]

    raw_institutions = extracted.get("institutions") or []
    institution_inputs: list[dict[str, Any]] = []
    if isinstance(raw_institutions, list):
        for item in raw_institutions:
            if isinstance(item, dict) and item.get("name"):
                institution_inputs.append(
                    {
                        "name": str(item["name"]).strip(),
                        "institution_type": str(
                            item.get("institution_type") or "other"
                        ).lower(),
                        "country": item.get("country"),
                        "city": item.get("city"),
                    }
                )

    verified_data: dict[str, Any] = {"institutions": []}
    if institution_inputs:
        try:
            verified_data = _verify_institutions(institution_inputs, settings)
        except ValidationFailed:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Institution verification failed")
            raise ValidationFailed(f"Institution verification failed: {exc}") from exc

    institutions: list[EducationInstitutionCheck] = []
    for item in verified_data.get("institutions") or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        inst_type = str(item.get("institution_type") or "other").lower()
        if inst_type not in ("school", "college", "university", "board", "other"):
            inst_type = "other"
        conf = str(item.get("confidence") or "low").lower()
        if conf not in ("high", "medium", "low"):
            conf = "low"
        institutions.append(
            EducationInstitutionCheck(
                name=str(item["name"]).strip(),
                institution_type=inst_type,  # type: ignore[arg-type]
                country=(str(item["country"]).strip() if item.get("country") else None),
                city=(str(item["city"]).strip() if item.get("city") else None),
                verified=bool(item.get("verified")),
                confidence=conf,  # type: ignore[arg-type]
                verification_note=str(item.get("verification_note") or "").strip()
                or "Could not confirm this institution.",
                source_hint=(
                    str(item["source_hint"]).strip() if item.get("source_hint") else None
                ),
            )
        )

    readable = any(d.readable for d in doc_summaries)
    looks_edu = any(d.looks_like_education_document for d in doc_summaries)
    all_verified = bool(institutions) and all(i.verified for i in institutions)
    any_verified = any(i.verified for i in institutions)

    checks = EducationVerificationChecks(
        documents_provided=len(docs),
        documents_readable=readable,
        looks_like_education_documents=looks_edu,
        all_institutions_verified=all_verified,
        any_institution_verified=any_verified,
    )

    if not readable:
        return EducationVerificationResult(
            status="unreadable",
            verified=False,
            message="Could not read the uploaded documents clearly. Upload sharper PDF scans or photos.",
            documents=doc_summaries,
            institutions=institutions,
            checks=checks,
            disclaimer=disclaimer,
        )

    if not looks_edu:
        return EducationVerificationResult(
            status="not_education_document",
            verified=False,
            message="The uploaded files do not look like education documents. Upload marks sheets, grade sheets, or transcripts.",
            documents=doc_summaries,
            institutions=institutions,
            checks=checks,
            disclaimer=disclaimer,
        )

    if not institutions:
        return EducationVerificationResult(
            status="unverified",
            verified=False,
            message="Documents were read but no school, college, or university name could be identified for verification.",
            documents=doc_summaries,
            institutions=[],
            checks=checks,
            disclaimer=disclaimer,
        )

    if all_verified:
        names = ", ".join(i.name for i in institutions)
        return EducationVerificationResult(
            status="verified",
            verified=True,
            message=(
                f"Documents verified. The following institution(s) appear to be real places: {names}."
            ),
            documents=doc_summaries,
            institutions=institutions,
            checks=checks,
            disclaimer=disclaimer,
        )

    if any_verified:
        verified_names = ", ".join(i.name for i in institutions if i.verified)
        unverified_names = ", ".join(i.name for i in institutions if not i.verified)
        return EducationVerificationResult(
            status="partial",
            verified=False,
            message=(
                f"Partial verification. Confirmed real: {verified_names or 'none'}. "
                f"Could not confirm: {unverified_names or 'none'}."
            ),
            documents=doc_summaries,
            institutions=institutions,
            checks=checks,
            disclaimer=disclaimer,
        )

    return EducationVerificationResult(
        status="unverified",
        verified=False,
        message="Documents were read but named institution(s) could not be confirmed as real places.",
        documents=doc_summaries,
        institutions=institutions,
        checks=checks,
        disclaimer=disclaimer,
    )
