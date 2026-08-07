"""CV screening service — upload, overrides, ranking, hire."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BusinessRuleViolation, ConflictError, EntityNotFound, ValidationFailed
from app.ingestion.cv_intake import store_cv_upload, store_fetched_cv
from app.ingestion.gmail_ingestor import fetch_gmail_submissions
from app.ingestion.google_form_ingestor import fetch_form_submissions
from app.integration.event_bus_stub import publish_event
from app.models.cv_screening import Candidate, CandidateRanking, CandidateScore, JobDescription
from app.models.employees import Employee
from app.pipeline import run_cv_pipeline
from app.ranking.candidate_ranker import rank_candidates_for_job
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.cv_screening import (
    CandidateAssignRequest,
    CandidateEvaluation,
    CandidateRead,
    CandidateUpdate,
    CvSourceResult,
    CvSyncResult,
    HireRequest,
    RankingRow,
    ScoreOverrideRequest,
    SkillEvaluationRow,
)
from app.scoring.cv_job_evaluator import evaluate_cv_against_job
from app.scoring.cv_job_matcher import OpenJobSummary, match_candidate_to_job
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
    if cand.job_description_id is None:
        raise BusinessRuleViolation(
            "This candidate is not yet assigned to a job description — assign it to a job "
            "before requesting an evaluation."
        )
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

    parsed = cand.parsed_data or {}
    cv_text = str(parsed.get("raw_text") or "")
    ai = evaluate_cv_against_job(
        cv_text=cv_text,
        job_title=job.title,
        description_text=job.description_text or "",
        requirements_text=job.requirements_text,
        settings=get_settings(),
        heuristic_overall_score=overall,
        heuristic_strengths=strengths,
        heuristic_gaps=gaps,
    )

    # Prefer AI-written bullets when present; keep criterion bullets as fallback.
    out_strengths = ai.strengths or strengths
    out_gaps = ai.gaps or gaps

    return CandidateEvaluation(
        candidate_id=cand.id,
        job_description_id=job.id,
        job_title=job.title,
        overall_score=overall,
        rank_position=rank_pos,
        rating_out_of_10=ai.rating_out_of_10,
        recommendation=ai.recommendation,  # type: ignore[arg-type]
        recommendation_label=ai.recommendation_label,
        summary=ai.summary,
        why_accepted=ai.why_accepted,
        why_rejected=ai.why_rejected,
        strengths=out_strengths,
        gaps=out_gaps,
        skills=skill_evals,
    )


def list_unassigned_candidates(
    db: Session, *, page: int = 1, page_size: int = 20
) -> PaginatedResponse[CandidateRead]:
    """Candidates fetched automatically that haven't been matched/routed to a
    job yet — FEATURE_CV_SCREENING.md §11."""
    q = db.query(Candidate).filter(Candidate.job_description_id.is_(None))
    total = q.count()
    rows = (
        q.order_by(Candidate.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return PaginatedResponse(
        items=[CandidateRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def assign_candidate_to_job(
    db: Session, auth: AuthContext, candidate_id: int, payload: CandidateAssignRequest
) -> Candidate:
    """HR manually routes an unassigned (or misassigned) candidate to a job,
    then runs the parse/score/rank pipeline against that job's criteria."""
    cand = get_candidate(db, candidate_id)
    job = (
        db.query(JobDescription)
        .filter(JobDescription.id == payload.job_description_id)
        .one_or_none()
    )
    if job is None:
        raise EntityNotFound(f"Job description {payload.job_description_id} not found")

    before = {"job_description_id": cand.job_description_id}
    cand.job_description_id = job.id
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="candidate.assigned_to_job",
        entity_type="candidate",
        entity_id=cand.id,
        before_state=before,
        after_state={"job_description_id": job.id},
    )
    try:
        run_cv_pipeline(cand.id, db)
    except Exception:
        pass
    return get_candidate(db, cand.id)


def sync_cv_sources(db: Session, auth: AuthContext) -> CvSyncResult:
    """Fetches new CVs from Gmail + Google Form, dedupes, stores them
    unassigned, then AI-matches each against open job descriptions —
    auto-assigning above the confidence threshold, leaving the rest in the
    Unassigned pool for HR to route manually. FEATURE_CV_SCREENING.md §11."""
    settings = get_settings()

    open_jobs = db.query(JobDescription).filter(JobDescription.status == "open").all()
    open_job_summaries = [
        OpenJobSummary(
            id=j.id,
            title=j.title,
            description_text=j.description_text,
            requirements_text=j.requirements_text,
        )
        for j in open_jobs
    ]

    fetch_results = [
        fetch_gmail_submissions(settings),
        fetch_form_submissions(settings),
    ]

    source_results: list[CvSourceResult] = []
    all_candidates: list[Candidate] = []
    auto_matched = 0
    unassigned = 0
    duplicates_skipped = 0

    for fetch_result in fetch_results:
        fetched_count = 0
        for submission in fetch_result.submissions:
            existing = (
                db.query(Candidate)
                .filter(
                    Candidate.source == fetch_result.source,
                    Candidate.source_ref == submission.source_ref,
                )
                .one_or_none()
            )
            if existing:
                duplicates_skipped += 1
                continue

            try:
                candidate = store_fetched_cv(
                    db,
                    source=fetch_result.source,
                    source_ref=submission.source_ref,
                    filename=submission.cv_filename,
                    content=submission.cv_bytes,
                    full_name=submission.full_name,
                    email=submission.email,
                    phone=submission.phone,
                    submitted_at=submission.submitted_at,
                )
            except ValidationFailed:
                continue  # unreadable/oversized file — skip, don't fail the whole sync

            try:
                run_cv_pipeline(candidate.id, db)  # parse-only: job_description_id is still None
            except Exception:
                pass

            cv_text = (candidate.parsed_data or {}).get("raw_text", "")
            match_result = match_candidate_to_job(
                cv_text, submission.position_hint, open_job_summaries, settings
            )
            candidate.match_confidence = match_result.confidence
            candidate.match_reasoning = match_result.reasoning
            db.flush()

            if (
                match_result.job_description_id is not None
                and match_result.confidence >= settings.cv_auto_match_min_confidence
            ):
                candidate.job_description_id = match_result.job_description_id
                db.flush()
                audit_service.log_from_auth(
                    db,
                    auth,
                    action="candidate.matched_to_job",
                    entity_type="candidate",
                    entity_id=candidate.id,
                    after_state={
                        "job_description_id": match_result.job_description_id,
                        "confidence": match_result.confidence,
                        "reasoning": match_result.reasoning,
                    },
                )
                try:
                    run_cv_pipeline(candidate.id, db)
                except Exception:
                    pass
                auto_matched += 1
            else:
                unassigned += 1

            fetched_count += 1
            all_candidates.append(get_candidate(db, candidate.id))

        source_results.append(
            CvSourceResult(
                source=fetch_result.source,
                configured=fetch_result.configured,
                fetched=fetched_count,
                message=fetch_result.message,
            )
        )

    audit_service.log_from_auth(
        db,
        auth,
        action="candidate.cv_sync_run",
        entity_type="candidate_import",
        entity_id=0,
        after_state={
            "total_fetched": len(all_candidates),
            "auto_matched": auto_matched,
            "unassigned": unassigned,
            "duplicates_skipped": duplicates_skipped,
            "sources": [r.model_dump() for r in source_results],
        },
    )

    return CvSyncResult(
        sources=source_results,
        total_fetched=len(all_candidates),
        auto_matched=auto_matched,
        unassigned=unassigned,
        duplicates_skipped=duplicates_skipped,
        candidates=[CandidateRead.model_validate(c) for c in all_candidates],
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
