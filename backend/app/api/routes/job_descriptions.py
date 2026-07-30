"""Job description routes — API_ENDPOINTS.md §4."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.schemas.common import AuthContext, MessageResponse, PaginatedResponse
from app.schemas.job_descriptions import (
    JobDescriptionCreate,
    JobDescriptionRead,
    JobDescriptionUpdate,
    ScoringCriteriaCreate,
    ScoringCriteriaRead,
    ScoringCriteriaReplace,
    ScoringCriteriaUpdate,
)
from app.services import job_description_service as jd_service
from app.reporting import word_export
from pathlib import Path
from app.core.config import get_settings

router = APIRouter(tags=["job-descriptions"])


@router.get("/job-descriptions", response_model=PaginatedResponse[JobDescriptionRead])
def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("job_descriptions", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: int | None = None,
    status: str | None = None,
) -> PaginatedResponse[JobDescriptionRead]:
    return jd_service.list_job_descriptions(
        db, page=page, page_size=page_size, department_id=department_id, status=status
    )


@router.post("/job-descriptions", response_model=JobDescriptionRead, status_code=201)
def create_job(
    payload: JobDescriptionCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("job_descriptions", "write"))],
) -> JobDescriptionRead:
    return JobDescriptionRead.model_validate(jd_service.create_job_description(db, auth, payload))


@router.get("/job-descriptions/{job_id}", response_model=JobDescriptionRead)
def get_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("job_descriptions", "read"))],
) -> JobDescriptionRead:
    return JobDescriptionRead.model_validate(jd_service.get_job_description(db, job_id))


@router.patch("/job-descriptions/{job_id}", response_model=JobDescriptionRead)
def patch_job(
    job_id: int,
    payload: JobDescriptionUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("job_descriptions", "write"))],
) -> JobDescriptionRead:
    return JobDescriptionRead.model_validate(
        jd_service.update_job_description(db, auth, job_id, payload)
    )


@router.delete("/job-descriptions/{job_id}", response_model=JobDescriptionRead)
def close_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("job_descriptions", "write"))],
) -> JobDescriptionRead:
    return JobDescriptionRead.model_validate(jd_service.archive_job_description(db, auth, job_id))


@router.get("/job-descriptions/{job_id}/export")
def export_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("job_descriptions", "read"))],
) -> FileResponse:
    job = jd_service.get_job_description(db, job_id)
    out_dir = get_settings().data_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"job_{job_id}.txt"
    word_export.export_word(
        {"title": job.title, "body": job.description_text, "requirements": job.requirements_text},
        dest,
    )
    return FileResponse(dest, filename=dest.name)


@router.get("/job-descriptions/{job_id}/scoring-criteria", response_model=list[ScoringCriteriaRead])
def get_criteria(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("job_descriptions", "read"))],
) -> list[ScoringCriteriaRead]:
    return [ScoringCriteriaRead.model_validate(c) for c in jd_service.list_criteria(db, job_id)]


@router.post("/job-descriptions/{job_id}/scoring-criteria", response_model=list[ScoringCriteriaRead])
def set_criteria(
    job_id: int,
    payload: ScoringCriteriaReplace,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("job_descriptions", "write"))],
) -> list[ScoringCriteriaRead]:
    rows = jd_service.replace_criteria(db, auth, job_id, payload)
    return [ScoringCriteriaRead.model_validate(c) for c in rows]


@router.patch("/scoring-criteria/{criteria_id}", response_model=ScoringCriteriaRead)
def patch_criterion(
    criteria_id: int,
    payload: ScoringCriteriaUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("job_descriptions", "write"))],
) -> ScoringCriteriaRead:
    data = payload.model_dump(exclude_unset=True)
    # merge into create-shaped update
    from app.models.cv_screening import ScoringCriteria

    row = db.query(ScoringCriteria).filter(ScoringCriteria.id == criteria_id).one()
    merged = ScoringCriteriaCreate(
        criterion_name=data.get("criterion_name", row.criterion_name),
        weight=data.get("weight", row.weight),
        scoring_rules=data.get("scoring_rules", row.scoring_rules or {}),
    )
    return ScoringCriteriaRead.model_validate(
        jd_service.update_criterion(db, auth, criteria_id, merged)
    )


@router.delete("/scoring-criteria/{criteria_id}", response_model=MessageResponse)
def delete_criterion(
    criteria_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("job_descriptions", "write"))],
) -> MessageResponse:
    jd_service.delete_criterion(db, auth, criteria_id)
    return MessageResponse(message="Criterion deleted")
