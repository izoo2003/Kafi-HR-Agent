"""Cross-cutting multi-step orchestration."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolation, EntityNotFound
from app.ingestion.cv_intake import ensure_cv_bytes
from app.models.cv_screening import Candidate, CandidateScore, ScoringCriteria
from app.models.payroll import PayrollRun
from app.parsing.cv_parser import parse_cv
from app.ranking.candidate_ranker import rank_candidates_for_job
from app.scoring.cv_scorer import score_candidate


def run_cv_pipeline(candidate_id: int, db: Session) -> Candidate:
    """parse -> score -> ranking refresh."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).one_or_none()
    if candidate is None:
        raise EntityNotFound(f"Candidate {candidate_id} not found")

    try:
        ensure_cv_bytes(candidate)
        db.flush()
    except EntityNotFound:
        candidate.status = "uploaded"
        db.flush()
        raise BusinessRuleViolation(
            "CV file is missing — it may have been stored on a previous server"
        ) from None

    parsed = parse_cv(candidate.cv_file_path)
    if not (parsed.get("raw_text") or "").strip():
        candidate.status = "uploaded"
        db.flush()
        raise BusinessRuleViolation("CV parsing produced empty text — check the file")

    candidate.parsed_data = parsed
    if parsed.get("full_name") and not candidate.full_name:
        candidate.full_name = parsed["full_name"]
    if parsed.get("email") and not candidate.email:
        candidate.email = parsed["email"]
    if parsed.get("phone") and not candidate.phone:
        candidate.phone = parsed["phone"]
    candidate.status = "parsed"
    db.flush()

    if candidate.job_description_id is None:
        # Fetched but not yet matched/assigned to a job (FEATURE_CV_SCREENING.md §11) —
        # parsing is all we can do until it lands on a job description.
        return candidate

    criteria_rows = (
        db.query(ScoringCriteria)
        .filter(ScoringCriteria.job_description_id == candidate.job_description_id)
        .all()
    )
    if not criteria_rows:
        return candidate

    payload = [
        {"id": c.id, "weight": c.weight, "scoring_rules": c.scoring_rules or {}}
        for c in criteria_rows
    ]
    score_rows, _total = score_candidate(parsed, payload)

    db.query(CandidateScore).filter(CandidateScore.candidate_id == candidate.id).delete()
    db.flush()
    for row in score_rows:
        db.add(
            CandidateScore(
                candidate_id=candidate.id,
                scoring_criteria_id=row["scoring_criteria_id"],
                raw_score=row["raw_score"],
                notes=row.get("notes"),
            )
        )
    db.flush()

    candidate.status = "scored"
    db.flush()
    rank_candidates_for_job(db, candidate.job_description_id)
    return candidate


def run_payroll_generation(payroll_run_id: int, db: Session) -> PayrollRun:
    run = db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id).one_or_none()
    if run is None:
        raise BusinessRuleViolation(f"Payroll run {payroll_run_id} not found")
    raise BusinessRuleViolation(
        "Payroll generation not implemented yet — complete Phase 3 attendance first"
    )
