"""Shared CV-vs-not-CV classifier for automated intake (Outlook, WhatsApp, etc.).

Heuristic text scoring first; optional Gemini when the score is borderline and
GEMINI_API_KEY is configured. FEATURE_CV_SCREENING.md §11.
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

CV_EXTENSIONS = {".pdf", ".docx"}
# Heuristic: clearly a CV / clearly not / ask Gemini if key present
HEURISTIC_ACCEPT = 4
HEURISTIC_REJECT = 2

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


@dataclass
class CvClassification:
    is_cv: bool
    reason: str
    score: int = 0


def classify_cv_document(
    *,
    filename: str,
    content: bytes,
    settings: Settings | None = None,
) -> CvClassification:
    """Return whether the PDF/DOCX looks like a CV/resume."""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in CV_EXTENSIONS:
        return CvClassification(False, f"Unsupported file type '{suffix or 'unknown'}'", 0)
    if not content:
        return CvClassification(False, "Empty file", 0)

    name_lower = (filename or "").lower()
    if re.search(r"(cv|resume|curriculum)", name_lower):
        name_boost = 2
    elif re.search(r"(invoice|receipt|statement|po_|quote)", name_lower):
        name_boost = -3
    else:
        name_boost = 0

    text = _extract_text_from_bytes(filename, content)
    if not text.strip():
        # Unreadable binary — treat as possible CV if filename suggests it
        if name_boost > 0:
            return CvClassification(True, "Filename suggests CV; text could not be extracted", name_boost)
        return CvClassification(False, "No extractable text and filename does not suggest a CV", 0)

    score, reasons = _heuristic_score(text)
    score += name_boost
    if name_boost:
        reasons.append(f"filename_boost={name_boost}")

    if score >= HEURISTIC_ACCEPT:
        return CvClassification(True, "; ".join(reasons) or "Heuristic match", score)
    if score <= HEURISTIC_REJECT:
        return CvClassification(False, "; ".join(reasons) or "Does not look like a CV", score)

    # Borderline — optional Gemini
    if settings and (settings.gemini_api_key or "").strip() and not settings.gemini_api_key.startswith("your_"):
        gemini = _gemini_classify(text[:8000], filename, settings)
        if gemini is not None:
            return gemini

    # Conservative: accept borderline with some positive signals
    is_cv = score >= 3
    return CvClassification(
        is_cv,
        "; ".join(reasons) + ("; borderline accept" if is_cv else "; borderline reject"),
        score,
    )


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

    # Date ranges common on CVs (2020 – 2023, Jan 2021, etc.)
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


def _gemini_classify(text: str, filename: str, settings: Settings) -> CvClassification | None:
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
