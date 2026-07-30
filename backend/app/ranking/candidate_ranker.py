"""Write CandidateRanking rows for a job."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.cv_screening import Candidate, CandidateRanking


def refresh_rankings(db: Session, job_description_id: int, scored: list[dict]) -> list[CandidateRanking]:
    """
    scored: [{candidate_id, total_score}]
    Replaces rankings for the job.
    """
    db.query(CandidateRanking).filter(
        CandidateRanking.job_description_id == job_description_id
    ).delete()
    db.flush()

    ordered = sorted(scored, key=lambda r: r.get("total_score", 0), reverse=True)
    now = datetime.now(UTC)
    rows: list[CandidateRanking] = []
    for idx, item in enumerate(ordered, start=1):
        row = CandidateRanking(
            job_description_id=job_description_id,
            candidate_id=item["candidate_id"],
            total_score=float(item["total_score"]),
            rank_position=idx,
            computed_at=now,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return rows


def rank_candidates_for_job(db: Session, job_description_id: int) -> list[CandidateRanking]:
    """Recompute from existing CandidateScore totals via CandidateRanking payloads already scored."""
    from app.models.cv_screening import CandidateScore, ScoringCriteria

    candidates = (
        db.query(Candidate)
        .filter(
            Candidate.job_description_id == job_description_id,
            Candidate.status.in_(["scored", "shortlisted", "rejected", "hired", "parsed"]),
        )
        .all()
    )
    criteria = (
        db.query(ScoringCriteria)
        .filter(ScoringCriteria.job_description_id == job_description_id)
        .all()
    )
    criteria_payload = [
        {"id": c.id, "weight": c.weight, "scoring_rules": c.scoring_rules or {}} for c in criteria
    ]

    from app.scoring.cv_scorer import score_candidate

    scored_rows: list[dict] = []
    for cand in candidates:
        if not cand.parsed_data:
            continue
        # Prefer recompute from scores table if present
        existing = (
            db.query(CandidateScore).filter(CandidateScore.candidate_id == cand.id).all()
        )
        if existing and criteria_payload:
            # rebuild from stored raw scores
            score_map = {s.scoring_criteria_id: s.raw_score for s in existing}
            total = 0.0
            wsum = 0.0
            for c in criteria_payload:
                from app.scoring.cv_scorer import _max_points_for_rule

                max_pts = _max_points_for_rule(c["scoring_rules"]) or 1.0
                raw = score_map.get(c["id"])
                if raw is None:
                    continue
                total += (float(raw) / max_pts) * float(c["weight"])
                wsum += float(c["weight"])
            total_score = (total / wsum) * 100 if wsum else 0.0
        else:
            _, total_score = score_candidate(cand.parsed_data, criteria_payload)
        scored_rows.append({"candidate_id": cand.id, "total_score": total_score})

    return refresh_rankings(db, job_description_id, scored_rows)
