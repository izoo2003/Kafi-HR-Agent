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
from app.reporting.excel_export import export_ranking_excel
from app.schemas.common import AuthContext, MessageResponse, PaginatedResponse
from app.schemas.cv_screening import (
    CandidateAssignRequest,
    CandidateEvaluation,
    CandidateRead,
    CandidateScoreRead,
    CandidateUpdate,
    CvSourceResult,
    CvSyncResult,
    HireRequest,
    RankingRow,
    ScoreOverrideRequest,
)
from app.schemas.employees import EmployeeRead
from app.services import audit_service, cv_screening_service as cv_service

router = APIRouter(tags=["cv-screening"])


@router.get("/cv-screening/source-check")
def cv_source_check() -> dict:
    """Unauthenticated diagnostic: can we reach each CV source? Peeks into inbox."""
    import datetime as dt
    import imaplib

    from app.core.config import get_settings
    from app.ingestion.imap_ingestor import _open_imap_client, probe_imap_connection

    settings = get_settings()
    sources: dict[str, dict] = {}

    # ── Webmail / IMAP ──
    imap_ok, imap_msg = probe_imap_connection(settings)
    imap_detail: dict = {
        "configured": bool((settings.imap_host or "").strip() and (settings.imap_password or "").strip()),
        "reachable": imap_ok,
        "detail": imap_msg,
        "connect_host": (settings.imap_connect_host or "").strip() or "(auto)",
    }
    if imap_ok:
        try:
            client = _open_imap_client(settings)
            typ, _ = client.select("INBOX")
            if typ == "OK":
                since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)).strftime("%d-%b-%Y")
                typ2, data = client.search(None, "SINCE", since)
                uids = data[0].split() if typ2 == "OK" and data and data[0] else []
                imap_detail["inbox_messages_since_90d"] = len(uids)
                # peek at last 3 messages for attachment info
                sample = []
                for uid in list(reversed(uids))[:3]:
                    typ3, hdr = client.fetch(uid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                    snippet = ""
                    if typ3 == "OK" and hdr and hdr[0]:
                        raw = hdr[0][1] if isinstance(hdr[0], tuple) else hdr[0]
                        snippet = raw.decode("utf-8", errors="ignore").strip()[:200] if isinstance(raw, bytes) else str(raw)[:200]
                    # check for attachments via BODYSTRUCTURE
                    typ4, bs = client.fetch(uid, "(BODYSTRUCTURE)")
                    bs_str = ""
                    if typ4 == "OK" and bs:
                        bs_str = str(bs[0])[:500]
                    has_attach = "attachment" in bs_str.lower() or ".pdf" in bs_str.lower() or ".docx" in bs_str.lower()
                    uid_s = uid.decode() if isinstance(uid, bytes) else str(uid)
                    sample.append({"uid": uid_s, "header": snippet, "has_cv_like_attach": has_attach})
                imap_detail["recent_sample"] = sample
            client.logout()
        except Exception as exc:
            imap_detail["peek_error"] = str(exc)
    sources["webmail"] = imap_detail

    # ── Google Form ──
    sheet_id = (settings.google_form_sheet_id or "").strip()
    gf: dict = {
        "configured": bool(sheet_id),
        "sheet_id_set": bool(sheet_id),
    }
    if sheet_id:
        try:
            import json as _json
            state_path = settings.data_dir / "google_form_state.json"
            last = 1
            if state_path.exists():
                last = int(_json.loads(state_path.read_text()).get("last_processed_row", 1))
            token_json_set = bool((settings.google_form_token_json or "").strip())
            creds_file = settings.resolved_path(settings.google_oauth_credentials_file)
            token_file = settings.resolved_path(settings.google_form_token_file)
            gf["last_processed_row"] = last
            gf["token_json_env_set"] = token_json_set
            gf["creds_file_exists"] = creds_file.exists() if creds_file else False
            gf["token_file_exists"] = token_file.exists() if token_file else False
            gf["detail"] = f"Sheet configured, last_processed_row={last}"
        except Exception as exc:
            gf["detail"] = f"check error: {exc}"
    else:
        gf["detail"] = "GOOGLE_FORM_RESPONSES_SHEET_ID not set"
    sources["google_form"] = gf

    enabled = [s.strip() for s in (settings.cv_sync_sources or "").split(",") if s.strip()]
    return {"enabled_sources": enabled, "sources": sources}


@router.post("/cv-screening/sync", response_model=CvSyncResult)
def sync_cv_sources(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("cv_screening", "write"))],
) -> CvSyncResult:
    try:
        return cv_service.sync_cv_sources(db, auth)
    except Exception as exc:  # noqa: BLE001
        return CvSyncResult(
            sources=[
                CvSourceResult(
                    source="webmail",
                    configured=True,
                    fetched=0,
                    message=f"Sync failed: {exc}",
                )
            ],
            total_fetched=0,
            auto_matched=0,
            unassigned=0,
            duplicates_skipped=0,
            restored_files=0,
            duplicates=[],
            candidates=[],
        )


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
    data, mime, filename = cv_service.get_candidate_cv_file(db, candidate_id)
    media = mime.split(";")[0]
    inline = media.startswith("image/") or media.startswith("text/") or media == "application/pdf"
    disposition = "inline" if inline else "attachment"
    return Response(
        content=data,
        media_type=media,
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
    cv_service.recompute_job_rankings(db, job_id)
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
