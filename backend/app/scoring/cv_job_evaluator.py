"""Gemini-based CV evaluation against a job posting's responsibilities/requirements.

Returns a rating out of 10 plus why-accept / why-reject narratives for HR review.
Falls back to a deterministic heuristic when GEMINI_API_KEY is missing or the call fails.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import Settings
from app.core.gemini_client import generate_content_with_fallback

logger = logging.getLogger(__name__)


@dataclass
class CvJobEvaluationResult:
    rating_out_of_10: float
    recommendation: str  # shortlist | consider | reject
    recommendation_label: str
    summary: str
    why_accepted: str
    why_rejected: str
    strengths: list[str]
    gaps: list[str]


def evaluate_cv_against_job(
    *,
    cv_text: str,
    job_title: str,
    description_text: str,
    requirements_text: str | None,
    settings: Settings,
    heuristic_overall_score: float | None = None,
    heuristic_strengths: list[str] | None = None,
    heuristic_gaps: list[str] | None = None,
) -> CvJobEvaluationResult:
    api_keys = _cv_eval_api_keys(settings)
    if api_keys:
        try:
            return _evaluate_with_gemini(
                cv_text=cv_text,
                job_title=job_title,
                description_text=description_text,
                requirements_text=requirements_text or "",
                settings=settings,
                api_keys=api_keys,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini CV evaluation failed, using heuristic: %s", exc)

    return _evaluate_heuristic(
        job_title=job_title,
        overall_score=heuristic_overall_score,
        strengths=heuristic_strengths or [],
        gaps=heuristic_gaps or [],
    )


def _cv_eval_api_keys(settings: Settings) -> list[str]:
    dedicated = settings.resolved_gemini_cv_match_api_keys()
    if dedicated:
        return dedicated
    return settings.resolved_gemini_api_keys()


def _cv_eval_models(settings: Settings) -> list[str]:
    return settings.resolved_gemini_cv_match_models()


def _evaluate_with_gemini(
    *,
    cv_text: str,
    job_title: str,
    description_text: str,
    requirements_text: str,
    settings: Settings,
    api_keys: list[str],
) -> CvJobEvaluationResult:
    prompt = f"""You are an HR screening assistant. Compare this candidate's CV against the job posting.

Job title: {job_title}

Job description / responsibilities:
\"\"\"{(description_text or "")[:4000]}\"\"\"

Requirements:
\"\"\"{(requirements_text or "")[:3000]}\"\"\"

CV text (truncated):
\"\"\"{(cv_text or "")[:7000]}\"\"\"

Score how well the CV matches the responsibilities and requirements.

Respond with STRICT JSON only (no markdown fences), exact shape:
{{
  "rating_out_of_10": <number 0-10, one decimal allowed>,
  "recommendation": "shortlist" | "consider" | "reject",
  "recommendation_label": "<short label, e.g. Recommend shortlist>",
  "summary": "<2-4 sentences overall assessment>",
  "why_accepted": "<paragraph: reasons this person SHOULD be accepted / shortlisted. If recommendation is reject, still list any redeeming strengths or write that acceptance is not recommended and why briefly.>",
  "why_rejected": "<paragraph: reasons this person SHOULD be rejected or concerns. If recommendation is shortlist, list residual risks or write that rejection is not recommended and why briefly.>",
  "strengths": ["<bullet>", "..."],
  "gaps": ["<bullet>", "..."]
}}

Rules:
- rating_out_of_10 must reflect fit to THIS posting's duties/requirements, not generic CV quality.
- Be specific (skills, experience, education) — avoid vague praise.
- recommendation: shortlist if strong fit (roughly 7+), consider if partial (roughly 4-6.9), reject if weak (<4).
"""

    response = generate_content_with_fallback(
        api_keys=api_keys,
        models=_cv_eval_models(settings),
        prompt=prompt,
        pool_id="cv_match",
    )
    data = _parse_json_response(response.text)

    rating = float(data.get("rating_out_of_10") or 0)
    rating = max(0.0, min(10.0, round(rating, 1)))
    rec = str(data.get("recommendation") or "consider").lower().strip()
    if rec not in {"shortlist", "consider", "reject"}:
        if rating >= 7:
            rec = "shortlist"
        elif rating >= 4:
            rec = "consider"
        else:
            rec = "reject"

    strengths = data.get("strengths") or []
    gaps = data.get("gaps") or []
    if not isinstance(strengths, list):
        strengths = [str(strengths)]
    if not isinstance(gaps, list):
        gaps = [str(gaps)]

    return CvJobEvaluationResult(
        rating_out_of_10=rating,
        recommendation=rec,
        recommendation_label=str(data.get("recommendation_label") or _label_for(rec)),
        summary=str(data.get("summary") or "").strip() or "Evaluation completed.",
        why_accepted=str(data.get("why_accepted") or "").strip()
        or "No acceptance rationale provided.",
        why_rejected=str(data.get("why_rejected") or "").strip()
        or "No rejection rationale provided.",
        strengths=[str(s) for s in strengths],
        gaps=[str(g) for g in gaps],
    )


def _evaluate_heuristic(
    *,
    job_title: str,
    overall_score: float | None,
    strengths: list[str],
    gaps: list[str],
) -> CvJobEvaluationResult:
    if overall_score is None:
        rating = 5.0
        rec = "consider"
        summary = (
            f"No AI key or ranking score available for {job_title}. "
            "Review the CV against the posting requirements manually."
        )
        why_accepted = (
            "Acceptance would require a manual review of experience against the job posting "
            "responsibilities and requirements."
        )
        why_rejected = (
            "Rejection cannot be justified automatically without an AI evaluation or skill scores. "
            "Do not reject based on this placeholder alone."
        )
    else:
        rating = round(max(0.0, min(10.0, overall_score / 10.0)), 1)
        if overall_score >= 75:
            rec = "shortlist"
        elif overall_score >= 45:
            rec = "consider"
        else:
            rec = "reject"
        summary = (
            f"Heuristic fit for {job_title}: {rating}/10 "
            f"(from rule-based score {overall_score:.1f}/100)."
        )
        why_accepted = (
            "Strengths supporting acceptance: " + "; ".join(strengths[:5])
            if strengths
            else "Limited positive signals from rule-based skill matching."
        )
        why_rejected = (
            "Gaps supporting rejection or caution: " + "; ".join(gaps[:5])
            if gaps
            else "No major gaps flagged by rule-based skill matching."
        )

    return CvJobEvaluationResult(
        rating_out_of_10=rating,
        recommendation=rec,
        recommendation_label=_label_for(rec),
        summary=summary,
        why_accepted=why_accepted,
        why_rejected=why_rejected,
        strengths=strengths,
        gaps=gaps,
    )


def _label_for(rec: str) -> str:
    return {
        "shortlist": "Recommend shortlist",
        "consider": "Consider with caution",
        "reject": "Recommend reject",
    }.get(rec, "Needs review")


def _parse_json_response(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    fence_match = re.search(r"\{.*\}", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(0)
    return json.loads(text)
