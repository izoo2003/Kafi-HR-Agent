"""Job description & scoring criteria service."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFound, ValidationFailed
from app.models.cv_screening import Candidate, CandidateRanking, CandidateScore, JobDescription, ScoringCriteria
from app.models.employees import Department
from app.schemas.common import AuthContext, PaginatedResponse
from app.core.config import get_settings
from app.schemas.job_descriptions import (
    JobDescriptionCreate,
    JobDescriptionRead,
    JobDescriptionUpdate,
    JobPostingAiDraftRequest,
    JobPostingAiDraftResult,
    JobPostingAiDraftSkill,
    ScoringCriteriaCreate,
    ScoringCriteriaReplace,
)
from app.scoring.job_posting_generator import append_application_link, generate_job_posting_draft
from app.services import audit_service
from app.services.linkedin_service import publish_job_if_open


def _application_form_url() -> str | None:
    url = (get_settings().google_form_url or "").strip()
    return url or None


def _to_read(job: JobDescription, applicants_count: int = 0) -> JobDescriptionRead:
    data = JobDescriptionRead.model_validate(job)
    return data.model_copy(
        update={
            "applicants_count": applicants_count,
            "application_form_url": _application_form_url(),
        }
    )


def _applicants_counts(db: Session, job_ids: list[int]) -> dict[int, int]:
    if not job_ids:
        return {}
    rows = (
        db.query(Candidate.job_description_id, func.count(Candidate.id))
        .filter(Candidate.job_description_id.in_(job_ids))
        .group_by(Candidate.job_description_id)
        .all()
    )
    return {int(job_id): int(count) for job_id, count in rows if job_id is not None}


def generate_ai_draft(db: Session, payload: JobPostingAiDraftRequest) -> JobPostingAiDraftResult:
    dept = db.query(Department).filter(Department.id == payload.department_id).one_or_none()
    if dept is None:
        raise ValidationFailed("department_id does not exist")
    settings = get_settings()
    draft = generate_job_posting_draft(
        title=payload.title,
        department_name=dept.name,
        settings=settings,
    )
    return JobPostingAiDraftResult(
        description_text=draft.description_text,
        requirements_text=draft.requirements_text,
        skills=[
            JobPostingAiDraftSkill(name=s.name, level=s.level) for s in draft.skills
        ],
        application_form_url=_application_form_url(),
    )


def _validate_skill_ratings(criteria: list[ScoringCriteriaCreate]) -> None:
    if not criteria:
        raise ValidationFailed("At least one skill is required")
    for c in criteria:
        if not (1 <= float(c.weight) <= 10):
            raise ValidationFailed(
                f"Skill level for '{c.criterion_name}' must be between 1 (very low) and 10 (expert)",
                details={"skill": c.criterion_name, "level": c.weight},
            )


def _normalize_skill_rules(item: ScoringCriteriaCreate) -> dict:
    """Ensure each skill scores via keyword match on the skill name."""
    rules = dict(item.scoring_rules or {})
    skill = item.criterion_name.strip()
    cfg = dict(rules.get("config") or {})
    keywords = cfg.get("keywords") or []
    if not keywords and skill:
        keywords = [skill]
    rules["type"] = "keyword_match"
    rules["config"] = {
        "keywords": keywords,
        "match_mode": cfg.get("match_mode") or "any",
        "points_per_match": float(cfg.get("points_per_match") or 10),
        "max_points": float(cfg.get("max_points") or 10),
        "proficiency": float(item.weight),
    }
    return rules


def list_job_descriptions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    department_id: int | None = None,
    status: str | None = None,
) -> PaginatedResponse[JobDescriptionRead]:
    q = db.query(JobDescription)
    if department_id is not None:
        q = q.filter(JobDescription.department_id == department_id)
    if status is not None:
        q = q.filter(JobDescription.status == status)
    total = q.count()
    rows = q.order_by(JobDescription.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    counts = _applicants_counts(db, [r.id for r in rows])
    return PaginatedResponse(
        items=[_to_read(r, counts.get(r.id, 0)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_job_description(db: Session, job_id: int) -> JobDescription:
    job = db.query(JobDescription).filter(JobDescription.id == job_id).one_or_none()
    if job is None:
        raise EntityNotFound(f"Job description {job_id} not found")
    return job


def get_job_description_read(db: Session, job_id: int) -> JobDescriptionRead:
    job = get_job_description(db, job_id)
    counts = _applicants_counts(db, [job.id])
    return _to_read(job, counts.get(job.id, 0))


def create_job_description(
    db: Session, auth: AuthContext, payload: JobDescriptionCreate
) -> JobDescription:
    if db.query(Department).filter(Department.id == payload.department_id).one_or_none() is None:
        raise ValidationFailed("department_id does not exist")
    data = payload.model_dump(exclude={"linkedin_account_names"})
    data["description_text"] = append_application_link(
        data["description_text"], get_settings().google_form_url
    )
    job = JobDescription(**data, created_by=auth.user_id)
    db.add(job)
    db.flush()
    if job.status == "open":
        publish_job_if_open(db, job, selected_names=payload.linkedin_account_names)
    audit_service.log_from_auth(
        db,
        auth,
        action="job_description.created",
        entity_type="job_description",
        entity_id=job.id,
        after_state={"title": job.title, "status": job.status},
    )
    return job


def update_job_description(
    db: Session, auth: AuthContext, job_id: int, payload: JobDescriptionUpdate
) -> JobDescription:
    job = get_job_description(db, job_id)
    before = {"title": job.title, "status": job.status}
    data = payload.model_dump(exclude_unset=True)
    selected_names = data.pop("linkedin_account_names", None)
    if "description_text" in data and data["description_text"] is not None:
        data["description_text"] = append_application_link(
            data["description_text"], get_settings().google_form_url
        )
    if "status" in data and data["status"] == "closed":
        action = "job_description.closed"
    else:
        action = "job_description.updated"
    for k, v in data.items():
        setattr(job, k, v)
    db.flush()
    if job.status == "open":
        publish_job_if_open(db, job, selected_names=selected_names)
    audit_service.log_from_auth(
        db,
        auth,
        action=action,
        entity_type="job_description",
        entity_id=job.id,
        before_state=before,
        after_state=data,
    )
    return job


def archive_job_description(db: Session, auth: AuthContext, job_id: int) -> JobDescription:
    return update_job_description(
        db, auth, job_id, JobDescriptionUpdate(status="closed")
    )


def delete_job_description(db: Session, auth: AuthContext, job_id: int) -> None:
    """Permanently remove a job posting and its criteria, candidates, and rankings."""
    from app.ingestion.employee_docs import delete_stored_file
    from app.services.cv_screening_service import delete_candidate

    job = get_job_description(db, job_id)
    before = {"title": job.title, "status": job.status, "department_id": job.department_id}

    candidate_ids = [
        row[0]
        for row in db.query(Candidate.id).filter(Candidate.job_description_id == job_id).all()
    ]
    for candidate_id in candidate_ids:
        delete_candidate(db, auth, candidate_id)

    db.query(CandidateRanking).filter(CandidateRanking.job_description_id == job_id).delete(
        synchronize_session=False
    )
    db.query(ScoringCriteria).filter(ScoringCriteria.job_description_id == job_id).delete(
        synchronize_session=False
    )

    if job.file_path:
        delete_stored_file(job.file_path)

    db.delete(job)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="job_description.deleted",
        entity_type="job_description",
        entity_id=job_id,
        before_state=before,
    )


def list_criteria(db: Session, job_id: int) -> list[ScoringCriteria]:
    get_job_description(db, job_id)
    return (
        db.query(ScoringCriteria)
        .filter(ScoringCriteria.job_description_id == job_id)
        .order_by(ScoringCriteria.id)
        .all()
    )


def replace_criteria(
    db: Session, auth: AuthContext, job_id: int, payload: ScoringCriteriaReplace
) -> list[ScoringCriteria]:
    get_job_description(db, job_id)
    _validate_skill_ratings(payload.criteria)

    existing = list_criteria(db, job_id)
    candidate_ids = [
        row[0]
        for row in db.query(Candidate.id).filter(Candidate.job_description_id == job_id).all()
    ]
    created: list[ScoringCriteria] = []

    overlap = min(len(existing), len(payload.criteria))
    for idx in range(overlap):
        item = payload.criteria[idx]
        row = existing[idx]
        row.criterion_name = item.criterion_name.strip()
        row.weight = float(item.weight)
        row.scoring_rules = _normalize_skill_rules(item)
        created.append(row)

    for item in payload.criteria[overlap:]:
        row = ScoringCriteria(
            job_description_id=job_id,
            criterion_name=item.criterion_name.strip(),
            weight=float(item.weight),
            scoring_rules=_normalize_skill_rules(item),
        )
        db.add(row)
        created.append(row)

    stale_rows = existing[overlap:]
    stale_ids = [row.id for row in stale_rows]
    if stale_ids:
        db.query(CandidateScore).filter(
            CandidateScore.scoring_criteria_id.in_(stale_ids)
        ).delete(synchronize_session=False)
        db.flush()
        for row in stale_rows:
            db.delete(row)

    if candidate_ids:
        db.query(CandidateRanking).filter(
            CandidateRanking.job_description_id == job_id
        ).delete(synchronize_session=False)

    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="scoring_criteria.updated",
        entity_type="job_description",
        entity_id=job_id,
        after_state={"count": len(created), "ratings": [c.weight for c in payload.criteria]},
    )

    if candidate_ids:
        from app.pipeline import run_cv_pipeline

        for candidate_id in candidate_ids:
            try:
                run_cv_pipeline(candidate_id, db)
            except Exception:
                # Criteria changes should not block saving the JD; candidates can be re-scored manually if needed.
                pass
    return created


def add_criterion(
    db: Session, auth: AuthContext, job_id: int, payload: ScoringCriteriaCreate
) -> ScoringCriteria:
    get_job_description(db, job_id)
    current = list_criteria(db, job_id)
    proposed = [
        ScoringCriteriaCreate(
            criterion_name=c.criterion_name, weight=c.weight, scoring_rules=c.scoring_rules or {}
        )
        for c in current
    ] + [payload]
    _validate_skill_ratings(proposed)
    row = ScoringCriteria(
        job_description_id=job_id,
        criterion_name=payload.criterion_name.strip(),
        weight=float(payload.weight),
        scoring_rules=_normalize_skill_rules(payload),
    )
    db.add(row)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="scoring_criteria.updated",
        entity_type="scoring_criteria",
        entity_id=row.id,
        after_state={"criterion_name": row.criterion_name, "weight": row.weight},
    )
    return row


def update_criterion(
    db: Session, auth: AuthContext, criteria_id: int, payload: ScoringCriteriaCreate | dict
) -> ScoringCriteria:
    row = db.query(ScoringCriteria).filter(ScoringCriteria.id == criteria_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"Scoring criteria {criteria_id} not found")
    data = payload if isinstance(payload, dict) else payload.model_dump(exclude_unset=True)
    before = {"weight": row.weight, "criterion_name": row.criterion_name}
    for k, v in data.items():
        if v is not None:
            setattr(row, k, v)
    siblings = list_criteria(db, row.job_description_id)
    proposed = [
        ScoringCriteriaCreate(
            criterion_name=c.criterion_name,
            weight=c.weight,
            scoring_rules=c.scoring_rules or {},
        )
        for c in siblings
    ]
    _validate_skill_ratings(proposed)
    if "criterion_name" in data or "weight" in data or "scoring_rules" in data:
        row.scoring_rules = _normalize_skill_rules(
            ScoringCriteriaCreate(
                criterion_name=row.criterion_name,
                weight=row.weight,
                scoring_rules=row.scoring_rules or {},
            )
        )
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="scoring_criteria.updated",
        entity_type="scoring_criteria",
        entity_id=row.id,
        before_state=before,
        after_state=data,
    )
    return row


def delete_criterion(db: Session, auth: AuthContext, criteria_id: int) -> None:
    row = db.query(ScoringCriteria).filter(ScoringCriteria.id == criteria_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"Scoring criteria {criteria_id} not found")
    job_id = row.job_description_id
    db.delete(row)
    db.flush()
    remaining = list_criteria(db, job_id)
    if remaining:
        proposed = [
            ScoringCriteriaCreate(
                criterion_name=c.criterion_name,
                weight=c.weight,
                scoring_rules=c.scoring_rules or {},
            )
            for c in remaining
        ]
        _validate_skill_ratings(proposed)
    audit_service.log_from_auth(
        db,
        auth,
        action="scoring_criteria.updated",
        entity_type="scoring_criteria",
        entity_id=criteria_id,
        after_state={"deleted": True},
    )
