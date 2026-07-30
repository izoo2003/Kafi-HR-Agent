"""Turns the scoring rubric + a role profile into the prompt sent to the LLM,
and resolves a numeric score into our verdict bands deterministically (never
trust the LLM's own label for this — only its score/analysis).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import load_role_profiles, load_scoring_rubric
from app.ingestion.position_matcher import get_role_profile


@dataclass(frozen=True)
class VerdictBand:
    label: str
    description: str


def resolve_verdict(score: float, rubric: dict[str, Any] | None = None) -> VerdictBand:
    rubric = rubric or load_scoring_rubric()
    for band in rubric["verdict_bands"]:
        if band["min_score"] <= score <= band["max_score"]:
            return VerdictBand(label=band["label"], description=band["description"])
    return VerdictBand(label="NOT RECOMMENDED", description="Score out of expected range")


def build_scoring_prompt(cv_text: str, position_title: str) -> str:
    rubric = load_scoring_rubric()
    role_profiles = load_role_profiles()
    role = get_role_profile(position_title, role_profiles)

    weights_lines = "\n".join(
        f"- {name.replace('_', ' ').title()}: {weight}%" for name, weight in rubric["weights"].items()
    )
    bands_lines = "\n".join(
        f"- {b['min_score']}-{b['max_score']}: {b['label']} ({b['description']})"
        for b in rubric["verdict_bands"]
    )
    required_skills = ", ".join(role.get("required_skills") or []) or "Not specified"
    nice_to_have = ", ".join(role.get("nice_to_have_skills") or []) or "Not specified"

    return f"""You are an expert technical recruiter scoring one candidate's CV for a
specific open role. Be rigorous, evidence-based, and consistent — score
based only on what the CV actually demonstrates, not assumptions.

## Role: {role.get('title', position_title)}
Role description: {role.get('description', 'N/A')}
Required skills: {required_skills}
Nice-to-have skills: {nice_to_have}
Minimum experience expected: {role.get('min_experience_years', 0)} year(s)

## Scoring rubric (weighted, must sum to a single 0-100 score)
{weights_lines}

## Verdict bands (for your reference only — do not output a verdict label,
the system computes it from your score)
{bands_lines}

## Candidate CV (raw extracted text)
\"\"\"
{cv_text}
\"\"\"

## Output
Respond with ONLY a valid JSON object, no markdown fences, no commentary,
in exactly this shape:
{{
  "score": <integer 0-100>,
  "education_summary": "<one line: degree, institution, notable academic detail>",
  "experience_summary": "<one line: current/most relevant role(s), duration>",
  "key_strengths": ["<bullet 1>", "<bullet 2>", "... 4-7 bullets total"],
  "hiring_summary": "<3-5 sentences. If the candidate is a good fit (score 55+): explain clearly WHY they should be selected for this company/role, citing concrete CV evidence. If they are a weak fit (score below 55): explain clearly WHY they should be rejected / not hired for this role, citing missing skills, weak experience, or misalignment. Always end with an explicit recommendation: select for interview, hold conditionally, or reject.>"
}}
"""
