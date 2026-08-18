"""Shared CV-vs-not-CV classifier for automated intake (mail, form, WhatsApp).

Heuristic text scoring first; optional Gemini (text or vision) when the score
is borderline. Images are accepted only when they look like a photographed /
scanned resume — not logos, signatures, banners, or inline email chrome.
FEATURE_CV_SCREENING.md §11.
"""
from __future__ import annotations

import io
import json
import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings

logger = logging.getLogger(__name__)

DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".txt"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff", ".bmp", ".heic", ".heif"}
CV_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

# Heuristic: clearly a CV / clearly not / ask Gemini if key present
HEURISTIC_ACCEPT = 4
HEURISTIC_REJECT = 2
MIN_IMAGE_BYTES = 40 * 1024  # logos / signatures / icons are almost always smaller
MIN_IMAGE_SIDE_PX = 500  # CV photos are page-sized; signatures are not
MAX_BANNER_ASPECT = 4.5  # wide banners / email footers

RESUME_KEYWORDS = [
    r"\bcurriculum\s+vitae\b",
    r"\bresume\b",
    r"\bcv\b",
    r"\bwork\s+experience\b",
    r"\bprofessional\s+experience\b",
    r"\bemployment\s+history\b",
    r"\beducation\b",
    r"\bacademic\b",
    r"\bskills?\b",
    r"\btechnical\s+skills\b",
    r"\bcertifications?\b",
    r"\bprojects?\b",
    r"\breferences?\b",
    r"\bobjective\b",
    r"\bsummary\b",
    r"\bprofile\b",
    r"\binternship\b",
    r"\bbachelor\b",
    r"\bmaster'?s?\b",
    r"\buniversity\b",
    r"\bresponsibilities\b",
]

NON_CV_KEYWORDS = [
    r"\binvoice\b",
    r"\breceipt\b",
    r"\bstatement\s+of\s+account\b",
    r"\bpurchase\s+order\b",
    r"\bquotation\b",
    r"\bbank\s+statement\b",
    r"\btax\s+invoice\b",
    r"\bmeeting\s+minutes\b",
    r"\bagenda\b",
]

# Typical non-CV image names from mail clients and marketing
NON_CV_IMAGE_NAME = re.compile(
    r"(logo|signature|signoff|banner|footer|header|icon|favicon|watermark|"
    r"qr[-_]?code|barcode|spacer|pixel|tracking|social|linkedin[-_]?icon|"
    r"facebook|instagram|twitter|whatsapp[-_]?icon|outlook-|image0+\d|"
    r"img_?\d{3,}|photo[-_]?id|headshot|selfie|avatar|profile[-_]?pic|"
    r"cid:|untitled|att0+\d)",
    re.I,
)
CV_NAME_HINT = re.compile(r"(cv|resume|curriculum|vitae)", re.I)


@dataclass
class CvClassification:
    is_cv: bool
    reason: str
    score: int = 0


@dataclass
class AttachmentCandidate:
    filename: str
    content: bytes
    is_inline: bool = False


def pick_cv_attachment(
    candidates: list[AttachmentCandidate],
    settings: Settings | None = None,
    *,
    source: str = "email",
) -> tuple[str | None, bytes | None]:
    """Prefer a real PDF/DOCX CV; only keep an image if it classifies as a resume.

    Skips inline email images (signatures, logos) unless the filename itself
    clearly says CV/resume.
    """
    docs: list[AttachmentCandidate] = []
    images: list[AttachmentCandidate] = []
    for item in candidates:
        suffix = Path(item.filename or "").suffix.lower()
        if suffix in DOCUMENT_EXTENSIONS:
            docs.append(item)
        elif suffix in IMAGE_EXTENSIONS:
            images.append(item)

    for item in docs:
        classification = classify_cv_document(
            filename=item.filename, content=item.content, settings=settings, source=source
        )
        if classification.is_cv:
            return item.filename, item.content
        logger.info("Skipped document %s (not a CV): %s", item.filename, classification.reason)

    for item in images:
        if item.is_inline and not CV_NAME_HINT.search(item.filename or ""):
            logger.info("Skipped inline image %s", item.filename)
            continue
        classification = classify_cv_document(
            filename=item.filename, content=item.content, settings=settings, source=source
        )
        if classification.is_cv:
            return item.filename, item.content
        logger.info("Skipped image %s (not a CV): %s", item.filename, classification.reason)

    return None, None


def classify_cv_document(
    *,
    filename: str,
    content: bytes,
    settings: Settings | None = None,
    source: str = "email",
) -> CvClassification:
    """Return whether the file looks like a CV/resume (PDF, DOCX, TXT, or image)."""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in CV_EXTENSIONS:
        return CvClassification(False, f"Unsupported file type '{suffix or 'unknown'}'", 0)
    if not content:
        return CvClassification(False, "Empty file", 0)

    if suffix in IMAGE_EXTENSIONS:
        return _classify_image(filename=filename, content=content, settings=settings, source=source)

    name_boost = _filename_boost(filename)
    text = _extract_text_from_bytes(filename, content)
    if not text.strip():
        if name_boost > 0:
            return CvClassification(True, "Filename suggests CV; text could not be extracted", name_boost)
        return CvClassification(False, "No extractable text and filename does not suggest a CV", 0)

    return _score_extracted_text(text, filename, settings, name_boost)


def extract_cv_text(filename: str, content: bytes, settings: Settings | None = None) -> str:
    """Text used by parsing — includes Gemini OCR for image CVs when configured."""
    suffix = Path(filename or "").suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return _ocr_image_text(content, filename, settings) or ""
    return _extract_text_from_bytes(filename, content)


def _filename_boost(filename: str) -> int:
    name_lower = (filename or "").lower()
    if CV_NAME_HINT.search(name_lower):
        return 2
    if re.search(r"(invoice|receipt|statement|po_|quote)", name_lower):
        return -3
    return 0


def _classify_image(
    *,
    filename: str,
    content: bytes,
    settings: Settings | None,
    source: str,
) -> CvClassification:
    name = filename or ""
    if NON_CV_IMAGE_NAME.search(name) and not CV_NAME_HINT.search(name):
        return CvClassification(False, "Image filename looks like a logo, signature, or mail chrome", 0)

    if len(content) < MIN_IMAGE_BYTES and not CV_NAME_HINT.search(name):
        return CvClassification(False, "Image is too small to be a photographed CV", 0)

    dims = _image_dimensions(content)
    if dims:
        width, height = dims
        short, long = min(width, height), max(width, height)
        if short < MIN_IMAGE_SIDE_PX and not CV_NAME_HINT.search(name):
            return CvClassification(
                False, f"Image is too small ({width}x{height}) — likely a logo or signature", 0
            )
        if short > 0 and (long / short) > MAX_BANNER_ASPECT:
            return CvClassification(False, "Image aspect ratio looks like a banner, not a CV page", 0)

    name_boost = _filename_boost(name)
    text = _ocr_image_text(content, name, settings)
    if text.strip():
        result = _score_extracted_text(text, name, settings, name_boost)
        if result.is_cv or result.score <= HEURISTIC_REJECT:
            return result

    vision = _gemini_classify_image(content, name, settings) if settings else None
    if vision is not None:
        return vision

    # Google Form "Upload your CV" field: a large unnamed photo of a page is likely a CV.
    # Mail attachments without a CV-like name stay rejected unless Gemini confirmed.
    looks_like_page = bool(dims) and min(dims) >= MIN_IMAGE_SIDE_PX and len(content) >= MIN_IMAGE_BYTES
    if source in {"form", "upload"} and (name_boost > 0 or looks_like_page):
        return CvClassification(True, "Form/upload image looks like a document page", name_boost)
    if name_boost > 0 and looks_like_page:
        return CvClassification(True, "Filename suggests CV and image is page-sized", name_boost)
    return CvClassification(False, "Image does not look like a CV/resume", 0)


def _score_extracted_text(
    text: str, filename: str, settings: Settings | None, name_boost: int
) -> CvClassification:
    score, reasons = _heuristic_score(text)
    score += name_boost
    if name_boost:
        reasons.append(f"filename_boost={name_boost}")

    if score >= HEURISTIC_ACCEPT:
        return CvClassification(True, "; ".join(reasons) or "Heuristic match", score)
    if score <= HEURISTIC_REJECT:
        return CvClassification(False, "; ".join(reasons) or "Does not look like a CV", score)

    if settings and _gemini_key(settings):
        gemini = _gemini_classify_text(text[:8000], filename, settings)
        if gemini is not None:
            return gemini

    is_cv = score >= 3
    return CvClassification(
        is_cv,
        "; ".join(reasons) + ("; borderline accept" if is_cv else "; borderline reject"),
        score,
    )


def _image_dimensions(content: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as img:
            return img.size
    except Exception:  # noqa: BLE001
        return None


def _ocr_image_text(content: bytes, filename: str, settings: Settings | None) -> str:
    if not settings or not _gemini_key(settings):
        return ""
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key.strip())
        model = genai.GenerativeModel(settings.gemini_model or "gemini-flash-latest")
        mime = _image_mime(filename)
        prompt = (
            "Extract all readable text from this image. If it is a CV/resume, transcribe "
            "the full visible content. If it is a logo, signature, icon, or photo of a person "
            "with little or no document text, reply with exactly: NOT_A_DOCUMENT"
        )
        response = model.generate_content(
            [prompt, {"mime_type": mime, "data": content[:4_000_000]}]
        )
        raw = (response.text or "").strip()
        if not raw or raw.upper().startswith("NOT_A_DOCUMENT"):
            return ""
        return raw
    except Exception:  # noqa: BLE001
        logger.warning("Gemini OCR failed for %s", filename, exc_info=True)
        return ""


def _gemini_classify_image(
    content: bytes, filename: str, settings: Settings | None
) -> CvClassification | None:
    if not settings or not _gemini_key(settings):
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key.strip())
        model = genai.GenerativeModel(settings.gemini_model or "gemini-flash-latest")
        mime = _image_mime(filename)
        prompt = f"""Decide if this IMAGE is a job-seeker CV/resume (a photographed or scanned document
with sections like experience, education, skills).

Filename: {filename}

Set is_cv=false for: logos, email signatures, icons, banners, selfies, ID cards, invoices,
screenshots that are not a resume, or any image that is not a CV.

Respond with STRICT JSON only:
{{"is_cv": true or false, "reason": "short explanation"}}
"""
        response = model.generate_content(
            [prompt, {"mime_type": mime, "data": content[:4_000_000]}]
        )
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return CvClassification(bool(data.get("is_cv")), str(data.get("reason") or "Gemini vision"), 0)
    except Exception:  # noqa: BLE001
        logger.warning("Gemini image classification failed for %s", filename, exc_info=True)
        return None


def _image_mime(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    return {
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
    }.get(suffix, "image/jpeg")


def _gemini_key(settings: Settings) -> str:
    key = (settings.gemini_api_key or "").strip()
    if not key or key.startswith("your_"):
        return ""
    return key


def _extract_text_from_bytes(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            import pdfplumber

            parts: list[str] = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages[:8]:
                    parts.append(page.extract_text() or "")
            return "\n".join(parts)
        if suffix == ".docx":
            import docx

            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            try:
                document = docx.Document(str(tmp_path))
                return "\n".join(p.text for p in document.paragraphs)
            finally:
                tmp_path.unlink(missing_ok=True)
        if suffix == ".txt":
            return content.decode("utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        logger.exception("CV text extraction failed for %s", filename)
    return ""


def _heuristic_score(text: str) -> tuple[int, list[str]]:
    lower = text.lower()
    score = 0
    reasons: list[str] = []

    hits = 0
    for pat in RESUME_KEYWORDS:
        if re.search(pat, lower, re.I):
            hits += 1
    score += min(hits, 8)
    if hits:
        reasons.append(f"resume_keywords={hits}")

    for pat in NON_CV_KEYWORDS:
        if re.search(pat, lower, re.I):
            score -= 3
            reasons.append(f"non_cv:{pat}")

    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        score += 1
        reasons.append("has_email")
    if re.search(r"(\+?\d[\d\s\-()]{8,}\d)", text):
        score += 1
        reasons.append("has_phone")

    if re.search(r"\b(20\d{2}|19\d{2})\s*[-–—]\s*(20\d{2}|19\d{2}|present|current)\b", lower):
        score += 1
        reasons.append("date_range")

    word_count = len(re.findall(r"\w+", text))
    if word_count < 40:
        score -= 2
        reasons.append("too_short")
    elif word_count > 120:
        score += 1
        reasons.append("substantial_text")

    return score, reasons


def _gemini_classify_text(text: str, filename: str, settings: Settings) -> CvClassification | None:
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key.strip())
        model = genai.GenerativeModel(settings.gemini_model or "gemini-flash-latest")
        prompt = f"""Decide if this document is a job-seeker CV/resume (not an invoice, letter, brochure, or random PDF).

Filename: {filename}

Document text (excerpt):
---
{text}
---

Respond with STRICT JSON only:
{{"is_cv": true or false, "reason": "short explanation"}}
"""
        response = model.generate_content(prompt)
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return CvClassification(bool(data.get("is_cv")), str(data.get("reason") or "Gemini"), 0)
    except Exception:  # noqa: BLE001
        logger.exception("Gemini CV classification failed")
        return None
