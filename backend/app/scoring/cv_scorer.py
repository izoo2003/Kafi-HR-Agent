"""CV scorer — evaluates scoring_rules against parsed_data."""
from __future__ import annotations

from typing import Any


def _max_points_for_rule(rule: dict[str, Any]) -> float:
    rtype = rule.get("type")
    cfg = rule.get("config") or {}
    if rtype == "keyword_match":
        return float(cfg.get("max_points") or 0)
    if rtype == "threshold_numeric":
        bands = cfg.get("bands") or []
        return float(max((b.get("points") or 0) for b in bands) if bands else 0)
    if rtype == "level_match":
        levels = cfg.get("levels") or {}
        return float(max(levels.values()) if levels else 0)
    if rtype == "manual_review":
        return float(cfg.get("max_points") or 0)
    return 0.0


def _score_keyword(parsed: dict[str, Any], cfg: dict[str, Any]) -> tuple[float | None, str]:
    keywords = [str(k).lower() for k in cfg.get("keywords") or []]
    if not keywords:
        return 0.0, "No keywords configured"
    haystack = " ".join(
        [
            " ".join(parsed.get("skills") or []),
            parsed.get("raw_text") or "",
        ]
    ).lower()
    matched = [k for k in keywords if k in haystack]
    mode = cfg.get("match_mode", "any")
    points_per = float(cfg.get("points_per_match") or 1)
    max_points = float(cfg.get("max_points") or len(keywords) * points_per)
    if mode == "all":
        raw = max_points if len(matched) == len(keywords) else 0.0
    else:
        raw = min(max_points, len(matched) * points_per)
    return raw, f"Matched {len(matched)}/{len(keywords)}: {', '.join(matched) or 'none'}"


def _score_threshold(parsed: dict[str, Any], cfg: dict[str, Any]) -> tuple[float | None, str]:
    field = cfg.get("field", "years_experience")
    value = parsed.get(field)
    try:
        value_f = float(value or 0)
    except (TypeError, ValueError):
        value_f = 0.0
    for band in cfg.get("bands") or []:
        lo = band.get("min")
        hi = band.get("max")
        if lo is not None and value_f < float(lo):
            continue
        if hi is not None and value_f > float(hi):
            continue
        return float(band.get("points") or 0), f"{field}={value_f} → band {lo}-{hi}"
    return 0.0, f"{field}={value_f} matched no band"


def _score_level(parsed: dict[str, Any], cfg: dict[str, Any]) -> tuple[float | None, str]:
    field = cfg.get("field", "education_level")
    level = parsed.get(field)
    if not level and parsed.get("education"):
        level = (parsed["education"][0] or {}).get("level")
    levels = cfg.get("levels") or {}
    if level and level in levels:
        return float(levels[level]), f"level={level}"
    return float(cfg.get("below_minimum_points") or 0), f"level={level or 'unknown'} below/unknown"


def score_candidate(
    parsed_data: dict[str, Any],
    criteria: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], float]:
    """
    criteria items: {id, weight, scoring_rules}
    Returns (score rows, weighted total 0-100-ish).
    """
    rows: list[dict[str, Any]] = []
    weighted_total = 0.0
    weight_used = 0.0

    for c in criteria:
        rule = c.get("scoring_rules") or {}
        rtype = rule.get("type")
        cfg = rule.get("config") or {}
        max_pts = _max_points_for_rule(rule) or 1.0

        if rtype == "manual_review":
            raw: float | None = None
            notes = "Pending manual review"
            norm = None
        elif rtype == "keyword_match":
            raw, notes = _score_keyword(parsed_data, cfg)
            norm = (raw or 0) / max_pts
        elif rtype == "threshold_numeric":
            raw, notes = _score_threshold(parsed_data, cfg)
            norm = (raw or 0) / max_pts
        elif rtype == "level_match":
            raw, notes = _score_level(parsed_data, cfg)
            norm = (raw or 0) / max_pts
        else:
            raw, notes = 0.0, f"Unknown rule type: {rtype}"
            norm = 0.0

        rows.append(
            {
                "scoring_criteria_id": c.get("id"),
                "raw_score": raw,
                "notes": notes,
                "max_points": max_pts,
                "normalized": norm,
                "weight": float(c.get("weight") or 0),
            }
        )
        if norm is not None:
            w = float(c.get("weight") or 0)
            weighted_total += norm * w
            weight_used += w

    # Scale to 0–100 using only resolved criteria weights
    if weight_used > 0:
        total = (weighted_total / weight_used) * 100.0
    else:
        total = 0.0
    return rows, round(total, 2)
