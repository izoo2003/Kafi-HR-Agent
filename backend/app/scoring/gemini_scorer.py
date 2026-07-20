"""Calls Gemini to score a parsed CV against a role, producing the same
shape of analysis as the reference ranking report (score, summaries, key
strengths, hiring narrative).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import google.generativeai as genai

from app.config import settings
from app.scoring.criteria import VerdictBand, build_scoring_prompt, resolve_verdict

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True


@dataclass
class ScoringResult:
    score: float
    verdict: VerdictBand
    education_summary: str
    experience_summary: str
    key_strengths: list[str]
    hiring_summary: str


def score_cv(cv_text: str, position_title: str) -> ScoringResult:
    _ensure_configured()

    prompt = build_scoring_prompt(cv_text, position_title)
    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(prompt)

    data = _parse_json_response(response.text)

    score = max(0, min(100, int(data["score"])))
    verdict = resolve_verdict(score)

    return ScoringResult(
        score=score,
        verdict=verdict,
        education_summary=data.get("education_summary", ""),
        experience_summary=data.get("experience_summary", ""),
        key_strengths=data.get("key_strengths", []),
        hiring_summary=data.get("hiring_summary", ""),
    )


def _parse_json_response(raw_text: str) -> dict:
    text = raw_text.strip()
    # Gemini sometimes wraps JSON in ```json ... ``` fences despite instructions.
    fence_match = re.search(r"\{.*\}", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(0)
    return json.loads(text)
