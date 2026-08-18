"""CV screening routes — API_ENDPOINTS.md §5."""
from __future__ import annotations

from typing import Annotated

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_permission
from app.models.cv_screening import CandidateScore
from app.pipeline import run_cv_pipeline
from app.ranking.candidate_ranker import rank_candidates_for_job
from app.reporting.excel_export import export_ranking_excel
from app.schemas.common import AuthContext, MessageResponse, PaginatedResponse
from app.schemas.cv_screening import (
    CandidateAssignRequest,
    CandidateEvaluation,
    CandidateRead,
    CandidateScoreRead,
    CandidateUpdate,
    CvSyncResult,
    HireRequest,
    RankingRow,
    ScoreOverrideRequest,
)
from app.schemas.employees import EmployeeRead
from app.services import audit_service, cv_screening_service as cv_service

router = APIRouter(tags=["cv-screening"])


@router.post("/cv-screening/sync", response_model=CvSyncResult)
def sync_cv_sources(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> CvSyncResult:
    return cv_service.sync_cv_sources(db, auth)


@router.get("/candidates/unassigned", response_model=PaginatedResponse[CandidateRead])
def list_unassigned_candidates(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CandidateRead]:
    return cv_service.list_unassigned_candidates(db, page=page, page_size=page_size)


@router.post("/candidates/{candidate_id}/assign", response_model=CandidateRead)
def assign_candidate(
    candidate_id: int,
    payload: CandidateAssignRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> CandidateRead:
    return CandidateRead.model_validate(
        cv_service.assign_candidate_to_job(db, auth, candidate_id, payload)
    )


@router.post("/job-descriptions/{job_id}/candidates", response_model=list[CandidateRead])
async def upload_cvs(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
    files: list[UploadFile] = File(...),
    full_name: str | None = Form(None),
    email: str | None = Form(None),
) -> list[CandidateRead]:
    payloads: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        payloads.append((f.filename or "cv.pdf", content))
    rows = cv_service.upload_candidates(
        db, auth, job_id, payloads, full_name=full_name, email=email
    )
    return [CandidateRead.model_validate(r) for r in rows]


@router.get("/job-descriptions/{job_id}/candidates", response_model=PaginatedResponse[CandidateRead])
def list_job_candidates(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[CandidateRead]:
    return cv_service.list_candidates(db, job_id, page=page, page_size=page_size)


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
) -> CandidateRead:
    return CandidateRead.model_validate(cv_service.get_candidate(db, candidate_id))


@router.get("/candidates/{candidate_id}/cv")
def download_candidate_cv(
    candidate_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
) -> Response:
    path, mime, filename = cv_service.get_candidate_cv_file(db, candidate_id)
    inline = mime.startswith("image/") or mime.startswith("text/") or mime == "application/pdf"
    disposition = "inline" if inline else "attachment"
    return FileResponse(
        path,
        media_type=mime.split(";")[0],
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": "private, max-age=60",
        },
    )


@router.patch("/candidates/{candidate_id}", response_model=CandidateRead)
def patch_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> CandidateRead:
    return CandidateRead.model_validate(
        cv_service.update_candidate(db, auth, candidate_id, payload)
    )


@router.delete("/candidates/{candidate_id}", response_model=MessageResponse)
def delete_candidate(
    candidate_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> MessageResponse:
    cv_service.delete_candidate(db, auth, candidate_id)
    return MessageResponse(message="Candidate removed")


@router.post("/candidates/{candidate_id}/parse", response_model=CandidateRead)
def parse_candidate(
    candidate_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> CandidateRead:
    return CandidateRead.model_validate(run_cv_pipeline(candidate_id, db))


@router.post("/candidates/{candidate_id}/score", response_model=CandidateRead)
def score_candidate_route(
    candidate_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> CandidateRead:
    return CandidateRead.model_validate(run_cv_pipeline(candidate_id, db))


@router.post("/job-descriptions/{job_id}/rank", response_model=list[RankingRow])
def rank_job(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> list[RankingRow]:
    rank_candidates_for_job(db, job_id)
    audit_service.log_from_auth(
        db, auth, action="candidate.ranked", entity_type="job_description", entity_id=job_id
    )
    return cv_service.get_ranking(db, job_id)


@router.get("/job-descriptions/{job_id}/ranking", response_model=list[RankingRow])
def get_ranking(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
) -> list[RankingRow]:
    return cv_service.get_ranking(db, job_id)


@router.post("/candidates/{candidate_id}/score-override", response_model=CandidateScoreRead)
def score_override(
    candidate_id: int,
    payload: ScoreOverrideRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "approve"))],
) -> CandidateScoreRead:
    row = cv_service.override_score(db, auth, candidate_id, payload)
    return CandidateScoreRead.model_validate(row)


@router.get("/candidates/{candidate_id}/scores", response_model=list[CandidateScoreRead])
def list_scores(
    candidate_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
) -> list[CandidateScoreRead]:
    rows = db.query(CandidateScore).filter(CandidateScore.candidate_id == candidate_id).all()
    return [CandidateScoreRead.model_validate(r) for r in rows]


@router.get("/candidates/{candidate_id}/evaluation", response_model=CandidateEvaluation)
def candidate_evaluation(
    candidate_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
) -> CandidateEvaluation:
    return cv_service.get_candidate_evaluation(db, candidate_id)


@router.get("/job-descriptions/{job_id}/report")
def export_report(
    job_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("cv_screening", "read"))],
) -> FileResponse:
    ranking = cv_service.get_ranking(db, job_id)
    out_dir = get_settings().data_dir / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"ranking_job_{job_id}.xlsx"
    export_ranking_excel(
        [{"rank": r.rank_position, "name": r.full_name, "email": r.email, "score": r.total_score, "status": r.status} for r in ranking],
        dest,
    )
    return FileResponse(
        dest,
        filename=dest.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.post("/candidates/{candidate_id}/hire", response_model=EmployeeRead)
def hire(
    candidate_id: int,
    payload: HireRequest,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "approve"))],
) -> EmployeeRead:
    emp = cv_service.hire_candidate(db, auth, candidate_id, payload)
    return EmployeeRead.model_validate(emp)
