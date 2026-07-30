"""CV screening service — upload, overrides, ranking, hire."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolation, ConflictError, EntityNotFound
from app.ingestion.cv_intake import store_cv_upload
from app.integration.event_bus_stub import publish_event
from app.models.cv_screening import Candidate, CandidateRanking, CandidateScore, JobDescription
from app.models.employees import Employee
from app.pipeline import run_cv_pipeline
from app.ranking.candidate_ranker import rank_candidates_for_job
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.cv_screening import (
    CandidateEvaluation,
    CandidateRead,
    CandidateUpdate,
    HireRequest,
    RankingRow,
    ScoreOverrideRequest,
    SkillEvaluationRow,
)
from app.scoring.cv_scorer import _max_points_for_rule
from app.services import audit_service


def list_candidates(
    db: Session,
    job_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[CandidateRead]:
    q = db.query(Candidate).filter(Candidate.job_description_id == job_id)
    total = q.count()
    rows = q.order_by(Candidate.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[CandidateRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_candidate(db: Session, candidate_id: int) -> Candidate:
    cand = db.query(Candidate).filter(Candidate.id == candidate_id).one_or_none()
    if cand is None:
        raise EntityNotFound(f"Candidate {candidate_id} not found")
    return cand


def upload_candidates(
    db: Session,
    auth: AuthContext,
    job_id: int,
    files: list[tuple[str, bytes]],
    *,
    full_name: str | None = None,
    email: str | None = None,
) -> list[Candidate]:
    job = db.query(JobDescription).filter(JobDescription.id == job_id).one_or_none()
    if job is None:
        raise EntityNotFound(f"Job description {job_id} not found")
    if job.status != "open":
        raise BusinessRuleViolation("CVs can only be uploaded to open job descriptions")

    created: list[Candidate] = []
    for filename, content in files:
        if email:
            dup = (
                db.query(Candidate)
                .filter(
                    Candidate.job_description_id == job_id,
                    Candidate.email == email.lower(),
                )
                .one_or_none()
            )
            if dup:
                raise ConflictError(
                    f"A candidate with email {email} already exists for this job",
                    details={"existing_candidate_id": dup.id},
                )
        cand = store_cv_upload(
            db,
            job_description_id=job_id,
            filename=filename,
            content=content,
            full_name=full_name,
            email=email.lower() if email else None,
        )
        audit_service.log_from_auth(
            db,
            auth,
            action="candidate.uploaded",
            entity_type="candidate",
            entity_id=cand.id,
            after_state={"job_description_id": job_id, "filename": filename},
        )
        try:
            run_cv_pipeline(cand.id, db)
        except Exception:
            pass
        created.append(get_candidate(db, cand.id))
    return created


def update_candidate(
    db: Session, auth: AuthContext, candidate_id: int, payload: CandidateUpdate
) -> Candidate:
    cand = get_candidate(db, candidate_id)
    before = {"status": cand.status, "full_name": cand.full_name}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(cand, k, v)
    db.flush()
    action = "candidate.status_changed" if "status" in data else "candidate.updated"
    audit_service.log_from_auth(
        db,
        auth,
        action=action,
        entity_type="candidate",
        entity_id=cand.id,
        before_state=before,
        after_state=data,
    )
    return cand


def override_score(
    db: Session, auth: AuthContext, candidate_id: int, payload: ScoreOverrideRequest
) -> CandidateScore:
    cand = get_candidate(db, candidate_id)
    row = (
        db.query(CandidateScore)
        .filter(
            CandidateScore.candidate_id == candidate_id,
            CandidateScore.scoring_criteria_id == payload.scoring_criteria_id,
        )
        .one_or_none()
    )
    before = {"raw_score": row.raw_score if row else None}
    if row is None:
        row = CandidateScore(
            candidate_id=candidate_id,
            scoring_criteria_id=payload.scoring_criteria_id,
            raw_score=payload.raw_score,
            notes=f"Override: {payload.reason}",
        )
        db.add(row)
    else:
        row.raw_score = payload.raw_score
        row.notes = f"Override: {payload.reason}"
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="candidate.score_override",
        entity_type="candidate_score",
        entity_id=row.id,
        before_state=before,
        after_state={"raw_score": payload.raw_score, "reason": payload.reason},
    )
    rank_candidates_for_job(db, cand.job_description_id)
    if cand.status in {"parsed", "uploaded", "scored"}:
        cand.status = "scored"
        db.flush()
    return row


def get_ranking(db: Session, job_id: int) -> list[RankingRow]:
    rankings = (
        db.query(CandidateRanking)
        .filter(CandidateRanking.job_description_id == job_id)
        .order_by(CandidateRanking.rank_position)
        .all()
    )
    out: list[RankingRow] = []
    for r in rankings:
        cand = get_candidate(db, r.candidate_id)
        scores = db.query(CandidateScore).filter(CandidateScore.candidate_id == cand.id).all()
        pending = any(
            (s.notes or "").find("pending_manual_review") >= 0 or s.raw_score is None for s in scores
        )
        out.append(
            RankingRow(
                candidate_id=cand.id,
                full_name=cand.full_name,
                email=cand.email,
                status=cand.status,
                total_score=r.total_score,
                rank_position=r.rank_position,
                pending_manual_review=pending,
            )
        )
    return out


def get_candidate_evaluation(db: Session, candidate_id: int) -> CandidateEvaluation:
    """Build a human-readable hire recommendation from scores vs job skills."""
    from app.models.cv_screening import ScoringCriteria

    cand = get_candidate(db, candidate_id)
    job = db.query(JobDescription).filter(JobDescription.id == cand.job_description_id).one()
    criteria = (
        db.query(ScoringCriteria)
        .filter(ScoringCriteria.job_description_id == job.id)
        .order_by(ScoringCriteria.id)
        .all()
    )
    score_rows = (
        db.query(CandidateScore).filter(CandidateScore.candidate_id == cand.id).all()
    )
    by_crit = {s.scoring_criteria_id: s for s in score_rows}
    ranking = (
        db.query(CandidateRanking)
        .filter(CandidateRanking.candidate_id == cand.id)
        .one_or_none()
    )

    skill_evals: list[SkillEvaluationRow] = []
    strengths: list[str] = []
    gaps: list[str] = []

    for c in criteria:
        rules = c.scoring_rules or {}
        cfg = rules.get("config") or {}
        max_pts = _max_points_for_rule(rules) or 10.0
        level = float(cfg.get("proficiency") or cfg.get("importance") or c.weight or 5)
        srow = by_crit.get(c.id)
        raw = srow.raw_score if srow else None
        notes = srow.notes if srow else None
        matched = raw is not None and float(raw) > 0
        skill_evals.append(
            SkillEvaluationRow(
                skill=c.criterion_name,
                required_level=level,
                matched=matched,
                raw_score=raw,
                max_points=max_pts,
                notes=notes,
            )
        )
        if matched:
            strengths.append(f"{c.criterion_name} (required level {level:.0f}/10) — found on CV")
        else:
            gaps.append(f"{c.criterion_name} (required level {level:.0f}/10) — not evidenced on CV")

    overall = float(ranking.total_score) if ranking else None
    rank_pos = ranking.rank_position if ranking else None

    matched_n = sum(1 for s in skill_evals if s.matched)
    total_n = len(skill_evals) or 1
    match_pct = matched_n / total_n

    if overall is None and not skill_evals:
        recommendation: str = "consider"
        label = "Needs review"
        summary = (
            f"{cand.full_name or 'This candidate'} has been uploaded but there are no skill "
            f"criteria on the job yet, so an automated accept/reject recommendation cannot be made."
        )
    elif overall is not None and overall >= 75 and match_pct >= 0.7:
        recommendation = "shortlist"
        label = "Recommend shortlist"
        summary = (
            f"{cand.full_name or 'This candidate'} scores {overall:.1f}/100 "
            f"(rank #{rank_pos if rank_pos else '—'}) and evidences {matched_n}/{total_n} required skills. "
            f"Overall fit is strong enough to shortlist for interview."
        )
    elif overall is not None and overall >= 45:
        recommendation = "consider"
        label = "Consider with caution"
        summary = (
            f"{cand.full_name or 'This candidate'} scores {overall:.1f}/100 "
            f"(rank #{rank_pos if rank_pos else '—'}) with {matched_n}/{total_n} skills matched. "
            f"There is partial fit — review the gaps below before deciding."
        )
    else:
        recommendation = "reject"
        label = "Recommend reject"
        score_bit = f"{overall:.1f}/100" if overall is not None else "unavailable"
        summary = (
            f"{cand.full_name or 'This candidate'} scores {score_bit} "
            f"and only matches {matched_n}/{total_n} required skills. "
            f"Based on the job skill profile, this CV is a weak fit and rejection is recommended "
            f"unless hiring for a junior/training track."
        )

    if gaps and recommendation == "shortlist":
        summary += f" Minor gaps: {', '.join(g.split(' (')[0] for g in gaps[:3])}."
    if strengths and recommendation == "reject":
        summary += f" Present strengths: {', '.join(s.split(' (')[0] for s in strengths[:3])}."

    parsed = cand.parsed_data or {}
    years = parsed.get("years_experience")
    if years is not None:
        try:
            y = float(years)
            if y <= 0 and recommendation != "reject":
                summary += " Note: parsed years of experience is 0 (common for current students) — verify education/internships manually."
        except (TypeError, ValueError):
            pass

    return CandidateEvaluation(
        candidate_id=cand.id,
        job_description_id=job.id,
        job_title=job.title,
        overall_score=overall,
        rank_position=rank_pos,
        recommendation=recommendation,  # type: ignore[arg-type]
        recommendation_label=label,
        summary=summary,
        strengths=strengths,
        gaps=gaps,
        skills=skill_evals,
    )


def hire_candidate(db: Session, auth: AuthContext, candidate_id: int, payload: HireRequest) -> Employee:
    cand = get_candidate(db, candidate_id)
    if cand.status == "hired":
        raise BusinessRuleViolation("Candidate already hired")
    if db.query(Employee).filter(Employee.employee_code == payload.employee_code).one_or_none():
        raise ConflictError("employee_code already exists")

    joined = date.fromisoformat(payload.date_joined) if payload.date_joined else date.today()
    emp = Employee(
        employee_code=payload.employee_code,
        full_name=cand.full_name or "Hired Candidate",
        department_id=payload.department_id,
        role_title=payload.role_title or "New Hire",
        employment_type="full_time",
        date_joined=joined,
        status="active",
        base_salary=Decimal(str(payload.base_salary)) if payload.base_salary is not None else None,
    )
    db.add(emp)
    cand.status = "hired"
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="candidate.status_changed",
        entity_type="candidate",
        entity_id=cand.id,
        after_state={"status": "hired", "employee_id": emp.id},
    )
    publish_event(
        "hr_admin.candidate.hired",
        {
            "candidate_id": cand.id,
            "job_description_id": cand.job_description_id,
            "employee_id": emp.id,
        },
    )
    return emp
