"""Gemini drafts for department-level job descriptions and SOPs."""
from __future__ import annotations

import logging

from app.core.config import Settings
from app.core.exceptions import BusinessRuleViolation
from app.core.gemini_client import GeminiQuotaExhausted, generate_content_with_fallback

logger = logging.getLogger(__name__)


def _api_keys_and_models(settings: Settings) -> tuple[list[str], list[str]]:
    job_keys = settings.resolved_gemini_job_posting_api_keys()
    if job_keys:
        return job_keys, settings.resolved_gemini_job_posting_models()
    keys = settings.resolved_gemini_api_keys()
    return keys, settings.resolved_gemini_models()


def generate_department_copy(*, name: str, kind: str, settings: Settings) -> str:
    department = (name or "").strip()
    if not department:
        raise BusinessRuleViolation("Enter a department name before generating with AI")
    if kind not in {"job_description", "sop"}:
        raise BusinessRuleViolation("kind must be job_description or sop")

    api_keys, models = _api_keys_and_models(settings)
    if not api_keys:
        raise BusinessRuleViolation(
            "Gemini is not configured — add GEMINI_API_KEY or GEMINI_JOB_POSTING_API_KEY "
            "in backend/.env to generate department JD and SOP text."
        )

    if kind == "job_description":
        prompt = f"""You write internal job descriptions for Kafi Group, a commodities company.

Write a clear job description for the department/role: {department}

Return PLAIN TEXT only (no markdown fences, no JSON). Use this structure:

Role overview
<2–4 sentences on what this department does at Kafi Group>

Key responsibilities
- <8–12 concrete duties>

Requirements
- <education, experience, tools, and working style>

Keep the tone precise and suitable for an internal HR file. Do not invent a different department name. Do not include salary, hashtags, or application instructions.
"""
    else:
        prompt = f"""You write standard operating procedures for Kafi Group, a commodities company.

Write SOPs for the department/role: {department}

Return PLAIN TEXT only (no markdown fences, no JSON). Use this structure:

Purpose
<1–2 sentences>

Daily operating procedure
1. ...
2. ...
(6–10 numbered steps)

Quality and escalation
- When to escalate
- What to record
- Who to notify (use role titles, not personal names)

Keep it practical and specific to this department. Do not invent a different department name.
"""

    try:
        response = generate_content_with_fallback(
            api_keys=api_keys,
            models=models,
            prompt=prompt,
            pool_id="department_copy",
        )
        text = (getattr(response, "text", "") or "").strip()
    except GeminiQuotaExhausted:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini department %s draft failed", kind)
        raise BusinessRuleViolation(f"Generate with AI failed: {exc}") from exc

    if not text:
        raise BusinessRuleViolation("Generate with AI returned empty text — try again")
    return text
