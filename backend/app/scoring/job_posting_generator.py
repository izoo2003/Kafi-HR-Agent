"""Gemini draft generator for job posting description + requirements from title & department."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import Settings
from app.core.exceptions import BusinessRuleViolation

logger = logging.getLogger(__name__)


@dataclass
class JobPostingDraft:
    description_text: str
    requirements_text: str


def generate_job_posting_draft(
    *,
    title: str,
    department_name: str,
    settings: Settings,
) -> JobPostingDraft:
    title = (title or "").strip()
    department_name = (department_name or "").strip()
    if not title:
        raise BusinessRuleViolation("Title is required to generate a job posting draft")
    if not department_name:
        raise BusinessRuleViolation("Department is required to generate a job posting draft")

    api_key = (settings.gemini_job_posting_api_key or "").strip()
    if not api_key or api_key.startswith("your_"):
        raise BusinessRuleViolation(
            "GEMINI_JOB_POSTING_API_KEY is not configured — add it in backend/.env "
            "to use AI Analyzer for job posting drafts (separate from CV screening)."
        )

    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(settings.gemini_job_posting_model or settings.gemini_model)

    prompt = f"""You are an HR job-posting writer for a company admin system.

Write a clear, professional job posting for:
- Title: {title}
- Department: {department_name}

Respond with STRICT JSON only (no markdown fences), exact shape:
{{
  "description_text": "<2-4 short paragraphs: role overview, day-to-day responsibilities, how the role fits the department. Plain text, use newlines between paragraphs.>",
  "requirements_text": "<bullet-style plain text of requirements: education, experience, skills, soft skills. Use lines starting with '- '. Keep it realistic for this title and department.>"
}}

Rules:
- Tailor content specifically to the title and department — do not invent a different role.
- Keep language precise and suitable for an internal HR tool (not marketing fluff).
- Do not include salary, equal-opportunity boilerplate, or application instructions.
- description_text must be at least 2 sentences; requirements_text must list at least 5 concrete requirements.
"""

    try:
        response = model.generate_content(prompt)
        data = _parse_json_response(response.text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini job posting draft failed")
        raise BusinessRuleViolation(f"AI Analyzer failed to generate draft: {exc}") from exc

    description = str(data.get("description_text") or "").strip()
    requirements = str(data.get("requirements_text") or "").strip()
    if not description or not requirements:
        raise BusinessRuleViolation("AI Analyzer returned an incomplete draft — try again")

    return JobPostingDraft(description_text=description, requirements_text=requirements)


def _parse_json_response(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    fence_match = re.search(r"\{.*\}", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(0)
    return json.loads(text)
