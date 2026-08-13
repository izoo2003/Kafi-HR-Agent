"""Gemini draft generator for job posting description, requirements, and skills."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from app.core.config import Settings
from app.core.exceptions import BusinessRuleViolation

logger = logging.getLogger(__name__)


@dataclass
class DraftSkill:
    name: str
    level: int  # 1–10


@dataclass
class JobPostingDraft:
    description_text: str
    requirements_text: str
    skills: list[DraftSkill] = field(default_factory=list)


def application_cta_block(form_url: str) -> str:
    url = (form_url or "").strip()
    if not url:
        return ""
    return (
        "\n\nHow to apply\n"
        "Submit your details and CV via this Google Form:\n"
        f"{url}"
    )


def append_application_link(description: str, form_url: str) -> str:
    """Ensure the Google Form apply CTA is present at the end of the description."""
    text = (description or "").rstrip()
    url = (form_url or "").strip()
    if not url:
        return text
    if url in text:
        return text
    return text + application_cta_block(url)


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
  "description_text": "<2-4 short paragraphs: role overview, day-to-day responsibilities, how the role fits the department. Plain text, use newlines between paragraphs. Do NOT include application instructions or any form URLs — those are added by the system.>",
  "requirements_text": "<bullet-style plain text of requirements: education, experience, soft skills. Use lines starting with '- '. Keep it realistic for this title and department.>",
  "skills": [
    {{"name": "<specific skill name>", "level": <integer 1-10>}}
  ]
}}

Rules:
- Tailor content specifically to the title and department — do not invent a different role.
- Keep language precise and suitable for an internal HR tool (not marketing fluff).
- Do not include salary, equal-opportunity boilerplate, or application instructions.
- description_text must be at least 2 sentences; requirements_text must list at least 5 concrete requirements.
- skills: return 5–10 concrete, scorable skills for this title (tools, languages, frameworks, domain skills).
- level: required proficiency from 1 (very low / nice-to-have) to 10 (expert / must-have core skill).
- Prefer specific skill names (e.g. "Python", "React", "Financial modeling") over vague ones ("hard work").
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

    skills = _parse_skills(data.get("skills"))
    if not skills:
        raise BusinessRuleViolation("AI Analyzer returned no skills — try again")

    description = append_application_link(description, settings.google_form_url)

    return JobPostingDraft(
        description_text=description,
        requirements_text=requirements,
        skills=skills,
    )


def _parse_skills(raw: object) -> list[DraftSkill]:
    if not isinstance(raw, list):
        return []
    out: list[DraftSkill] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("skill") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            level = int(round(float(item.get("level", 5))))
        except (TypeError, ValueError):
            level = 5
        level = max(1, min(10, level))
        out.append(DraftSkill(name=name, level=level))
    return out


def _parse_json_response(raw_text: str) -> dict:
    text = (raw_text or "").strip()
    fence_match = re.search(r"\{.*\}", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(0)
    return json.loads(text)
