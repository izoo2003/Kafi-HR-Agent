"""Matches a fetched CV to the best open Job Description — FEATURE_CV_SCREENING.md §11.

Primary: Gemini reads the CV text against every open JD and picks the best
match with a confidence score. Falls back to a deterministic keyword
matcher (title/requirements overlap) when GEMINI_API_KEY isn't set, so the
feature still works without an AI key.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class OpenJobSummary:
    id: int
    title: str
    description_text: str
    requirements_text: str | None


@dataclass
class CvJobMatchResult:
    job_description_id: int | None
    confidence: float  # 0.0–1.0
    reasoning: str


def match_candidate_to_job(
    cv_text: str,
    position_hint: str,
    open_jobs: list[OpenJobSummary],
    settings: Settings,
) -> CvJobMatchResult:
    if not open_jobs:
        return CvJobMatchResult(
            job_description_id=None, confidence=0.0, reasoning="No open job descriptions to match against."
        )

    if settings.gemini_api_key:
        try:
            return _match_with_gemini(cv_text, position_hint, open_jobs, settings)
        except Exception as exc:  # noqa: BLE001 — fall back rather than fail the whole sync
            logger.warning("Gemini CV-job match failed, falling back to keyword match: %s", exc)

    return _match_with_keywords(cv_text, position_hint, open_jobs)


def _match_with_gemini(
    cv_text: str,
    position_hint: str,
    open_jobs: list[OpenJobSummary],
    settings: Settings,
) -> CvJobMatchResult:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.gemini_model)

    jobs_payload = [
        {
            "id": job.id,
            "title": job.title,
            "description": (job.description_text or "")[:1500],
            "requirements": (job.requirements_text or "")[:1500],
        }
        for job in open_jobs
    ]

    prompt = f"""You are screening a candidate's CV to route it to the correct open job.

Candidate's stated position of interest (may be inaccurate or missing): "{position_hint}"

CV text (truncated):
\"\"\"{(cv_text or "")[:6000]}\"\"\"

Open job descriptions (JSON):
{json.dumps(jobs_payload, indent=2)}

Pick the single best-matching job_description_id for this candidate based on skills,
experience, and stated interest. If none are a reasonable match, return null.

Respond with STRICT JSON only, no markdown fences, in this exact shape:
{{"job_description_id": <int or null>, "confidence": <float 0-1>, "reasoning": "<one short sentence>"}}
"""

    response = model.generate_content(prompt)
    data = _parse_json_response(response.text)

    job_id = data.get("job_description_id")
    valid_ids = {job.id for job in open_jobs}
    if job_id is not None and int(job_id) not in valid_ids:
        job_id = None

    confidence = float(data.get("confidence") or 0.0)
    confidence = max(0.0, min(1.0, confidence))
    if job_id is None:
        confidence = 0.0

    return CvJobMatchResult(
        job_description_id=int(job_id) if job_id is not None else None,
        confidence=confidence,
        reasoning=str(data.get("reasoning") or "").strip() or "Gemini match",
    )


def _parse_json_response(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    fence_match = re.search(r"\{.*\}", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(0)
    return json.loads(text)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).strip()


def _match_with_keywords(
    cv_text: str, position_hint: str, open_jobs: list[OpenJobSummary]
) -> CvJobMatchResult:
    """Deterministic fallback: overlap between (position hint + CV text) and
    each job's title/requirements words. No external calls, always available."""
    haystack = _normalize(f"{position_hint} {cv_text}")
    haystack_words = set(haystack.split())

    best_job: OpenJobSummary | None = None
    best_score = 0.0

    for job in open_jobs:
        title_norm = _normalize(job.title)
        if title_norm and title_norm in haystack:
            # Direct title mention in the CV/position hint — strong signal.
            score = 0.75
        else:
            job_words = set(_normalize(f"{job.title} {job.requirements_text or ''}").split())
            job_words = {w for w in job_words if len(w) > 3}  # skip short stopword-ish tokens
            if not job_words:
                score = 0.0
            else:
                overlap = haystack_words & job_words
                score = len(overlap) / len(job_words)

        if score > best_score:
            best_score = score
            best_job = job

    if best_job is None or best_score <= 0.0:
        return CvJobMatchResult(
            job_description_id=None,
            confidence=0.0,
            reasoning="No keyword overlap found with any open job description.",
        )

    # Keyword overlap scores are inherently noisier than an LLM's — cap so this
    # path rarely crosses a default 0.55 auto-assign threshold without a strong signal.
    confidence = min(0.9, round(best_score, 2))
    return CvJobMatchResult(
        job_description_id=best_job.id,
        confidence=confidence,
        reasoning=f"Keyword overlap with '{best_job.title}' (no AI key configured).",
    )
