"""Job description & scoring criteria service."""
from __future__ import annotations

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleViolation, EntityNotFound, ValidationFailed
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
    JobPostingAiImageRequest,
    JobPostingAiImageResult,
    ScoringCriteriaCreate,
    ScoringCriteriaReplace,
)
from app.scoring.job_posting_generator import append_application_link, generate_job_posting_draft
from app.services import audit_service
from app.services.linkedin_service import publish_job_if_open

MAX_JOB_IMAGES = 8


def ensure_job_image_schema(db: Session) -> None:
    bind = db.get_bind()
    if bind is None:
        return
    dialect = bind.dialect.name
    if dialect == "sqlite":
        cols = {
            row[1] for row in db.execute(text("PRAGMA table_info(job_descriptions)")).fetchall()
        }
        if cols and "image_paths" not in cols:
            db.execute(text("ALTER TABLE job_descriptions ADD COLUMN image_paths JSON"))
        return
    if dialect == "postgresql":
        db.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS image_paths JSON"))


def _application_form_url() -> str | None:
    url = (get_settings().google_form_url or "").strip()
    return url or None


def _to_read(job: JobDescription, applicants_count: int = 0) -> JobDescriptionRead:
    data = JobDescriptionRead.model_validate(job)
    return data.model_copy(
        update={
            "applicants_count": applicants_count,
            "application_form_url": _application_form_url(),
            "image_paths": list(job.image_paths or []),
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


def generate_ai_image(db: Session, payload: JobPostingAiImageRequest) -> JobPostingAiImageResult:
    import base64

    from app.reporting.job_posting_poster import (
        append_apply_here_line,
        generate_default_template_poster_png,
        generate_hiring_poster_png,
    )
    from app.scoring.job_posting_generator import generate_job_posting_draft

    dept = db.query(Department).filter(Department.id == payload.department_id).one_or_none()
    if dept is None:
        raise ValidationFailed("department_id does not exist")

    settings = get_settings()
    # Always AI-draft content for the poster from title + department.
    draft = generate_job_posting_draft(
        title=payload.title.strip(),
        department_name=dept.name,
        settings=settings,
    )
    user_poster_description = (payload.poster_description_text or "").strip()
    user_requirements = (payload.requirements_text or "").strip()
    user_skills = [s.name.strip() for s in (payload.skills or []) if (s.name or "").strip()]
    use_default_template = not user_poster_description and not user_requirements and not user_skills

    poster_description = user_poster_description or draft.description_text
    requirements = user_requirements or draft.requirements_text
    skills = user_skills or [s.name for s in draft.skills if s.name.strip()]

    form_url = _application_form_url() or ""
    apply_email = (settings.hiring_apply_email or "hr@kafi-group.com").strip()
    if use_default_template:
        png = generate_default_template_poster_png(
            title=payload.title.strip(),
            description_text=poster_description,
            requirements_text=requirements,
            apply_email=apply_email,
        )
    else:
        png = generate_hiring_poster_png(
            title=payload.title.strip(),
            company_name=(settings.company_display_name or "Kafi Group").strip(),
            description_text=poster_description,
            requirements_text=requirements,
            skill_names=skills,
            form_url=form_url,
            apply_email=apply_email,
            settings=settings,
        )
    # Job description_text stays LinkedIn-safe: title line + apply CTA only.
    # Poster AI description is returned separately and must not be saved into
    # description_text / LinkedIn commentary.
    linkedin_safe = f"We're hiring: {payload.title.strip()}."
    linkedin_safe = append_apply_here_line(linkedin_safe, form_url)
    safe_title = "".join(c if c.isalnum() or c in "-_" else "-" for c in payload.title.strip())[:40]
    return JobPostingAiImageResult(
        image_base64=base64.b64encode(png).decode("ascii"),
        mime_type="image/png",
        filename=f"hiring-{safe_title or 'poster'}.png",
        description_text=linkedin_safe,
        poster_description_text=poster_description,
        application_form_url=form_url or None,
        requirements_text=requirements,
        skills=[JobPostingAiDraftSkill(name=name, level=5) for name in skills[:10]],
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
    ensure_job_image_schema(db)
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
    ensure_job_image_schema(db)
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
    ensure_job_image_schema(db)
    if db.query(Department).filter(Department.id == payload.department_id).one_or_none() is None:
        raise ValidationFailed("department_id does not exist")
    data = payload.model_dump(exclude={"linkedin_account_names"})
    data["description_text"] = append_application_link(
        data["description_text"], get_settings().google_form_url
    )
    data["image_paths"] = []
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
    for image_path in job.image_paths or []:
        delete_stored_file(image_path)

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


def add_job_images(
    db: Session,
    auth: AuthContext,
    job_id: int,
    files: list[tuple[str, bytes]],
) -> JobDescription:
    from sqlalchemy.orm.attributes import flag_modified

    from app.ingestion.employee_docs import store_job_image

    job = get_job_description(db, job_id)
    paths = list(job.image_paths or [])
    if not files:
        raise ValidationFailed("At least one image is required")
    if len(paths) + len(files) > MAX_JOB_IMAGES:
        raise ValidationFailed(f"At most {MAX_JOB_IMAGES} images per job posting")
    for filename, content in files:
        stored, _mime = store_job_image(job_id=job_id, filename=filename, content=content)
        paths.append(stored)
    job.image_paths = paths
    flag_modified(job, "image_paths")
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="job_description.images_added",
        entity_type="job_description",
        entity_id=job_id,
        after_state={"image_count": len(paths)},
    )
    return job


def read_job_image(db: Session, job_id: int, index: int) -> tuple[bytes, str]:
    import mimetypes
    from pathlib import Path

    from app.ingestion.employee_docs import read_stored_file

    job = get_job_description(db, job_id)
    paths = list(job.image_paths or [])
    if index < 0 or index >= len(paths):
        raise EntityNotFound(f"Job image {index} not found")
    path = paths[index]
    data = read_stored_file(path)
    name = Path(path).name if "://" not in path else path.rsplit("/", 1)[-1]
    mime = mimetypes.guess_type(name)[0] or "image/jpeg"
    return data, mime


def delete_job_image(db: Session, auth: AuthContext, job_id: int, index: int) -> JobDescription:
    from sqlalchemy.orm.attributes import flag_modified

    from app.ingestion.employee_docs import delete_stored_file

    job = get_job_description(db, job_id)
    paths = list(job.image_paths or [])
    if index < 0 or index >= len(paths):
        raise EntityNotFound(f"Job image {index} not found")
    removed = paths.pop(index)
    delete_stored_file(removed)
    job.image_paths = paths
    flag_modified(job, "image_paths")
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="job_description.image_removed",
        entity_type="job_description",
        entity_id=job_id,
        after_state={"image_count": len(paths)},
    )
    return job


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
