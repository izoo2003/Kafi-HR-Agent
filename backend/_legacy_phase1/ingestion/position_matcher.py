"""Best-effort matching of free-text 'position applied for' strings (email
subject/body, form field) against the role profiles in config/roles.yaml.

Falls back to the raw text (title-cased) if nothing matches, so a submission
is never dropped just because we haven't profiled that role yet — it will
use the `default` scoring profile instead.
"""
from __future__ import annotations

import re
from typing import Any


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


def clean_position_label(text: str) -> str:
    """Turns noisy email subjects into a short displayable position label.

    Examples:
      "Interested In Graphic Designer Position (Test)" -> "Graphic Designer"
      "Subject: Application for Sales Assistant" -> "Sales Assistant"
    """
    label = (text or "").split("\n", 1)[0].strip()
    label = re.sub(r"(?i)^subject:\s*", "", label)
    label = re.sub(
        r"(?i)^(interested\s+in|application\s+for|applying\s+for|re:|fw:)\s+",
        "",
        label,
    )
    label = re.sub(r"(?i)\s*\(test\)\s*", " ", label)
    label = re.sub(r"(?i)\s+position\s*$", "", label)
    label = re.sub(r"\s+", " ", label).strip(" -:")
    return label


def match_position(
    raw_text: str,
    role_profiles: dict[str, Any],
    fallback_label: str | None = None,
) -> str:
    """Returns the canonical role title (roles.yaml `title`) if a match is
    found via title/alias keyword matching, otherwise returns a cleaned
    fallback label (never the full email body).
    """
    normalized = _normalize(raw_text)

    best_match: str | None = None
    best_len = 0
    for role in role_profiles.get("roles", []):
        candidates = [role["title"], *role.get("aliases", [])]
        for candidate in candidates:
            candidate_norm = _normalize(candidate)
            if candidate_norm and candidate_norm in normalized and len(candidate_norm) > best_len:
                best_match = role["title"]
                best_len = len(candidate_norm)

    if best_match:
        return best_match

    cleaned = clean_position_label(fallback_label or raw_text)
    return cleaned.title() if cleaned else "Unspecified"


def get_role_profile(position_title: str, role_profiles: dict[str, Any]) -> dict[str, Any]:
    """Looks up the full role profile dict for a canonical title, falling
    back to the `default` profile."""
    for role in role_profiles.get("roles", []):
        if role["title"].lower() == position_title.lower():
            return role
    default = dict(role_profiles.get("default", {}))
    default["title"] = position_title
    return default
