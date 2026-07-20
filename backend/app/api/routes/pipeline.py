"""Action endpoints that trigger the ingestion/scoring/ranking pipeline.

Long work (Gmail/Gemini) runs in a background thread so the HTTP response
returns immediately and the dashboard can poll /pipeline/status instead of
hanging for many minutes on one request.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.jobs import get_job_state, try_start_job
from app.api.schemas import FetchResult, PipelineRunResult, ScoreResult
from app.db.database import get_session
from app.db.models import Application, ApplicationStatus, SourceChannel
from app.pipeline import (
    fetch_submissions,
    generate_all_reports,
    parse_and_score_pending,
    rank_all,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/status")
def pipeline_status() -> dict:
    """Poll this after fetch/score/rank/run-all. Those POSTs only *start* a
    background job and return quickly with status=running; this endpoint
    shows whether the job finished and what it produced."""
    return get_job_state()


@router.post("/fetch")
def fetch(source: str = "all") -> dict:
    """Starts a background fetch. Response is usually status=running — poll
    GET /pipeline/status until status is succeeded/failed. new_applications=0
    means nothing new (already ingested / already labeled in Gmail)."""
    sources = None if source == "all" else [SourceChannel(source)]

    def worker() -> dict:
        with get_session() as db:
            created = fetch_submissions(db, sources)
            pending = (
                db.query(Application)
                .filter(
                    Application.status.in_(
                        [ApplicationStatus.RECEIVED, ApplicationStatus.PARSED]
                    )
                )
                .count()
            )
        if created == 0 and pending == 0:
            msg = "No new CVs found. Everything already ingested and scored."
        elif created == 0 and pending > 0:
            msg = (
                f"No new CVs (already fetched earlier). "
                f"{pending} still waiting to be scored — click Score Pending."
            )
        else:
            msg = f"Ingested {created} new CV(s). {pending} waiting to be scored."
        return FetchResult(
            new_applications=created, pending_unscored=pending, message=msg
        ).model_dump()

    return try_start_job("fetch", worker)


@router.post("/score")
def score() -> dict:
    """Starts background scoring for RECEIVED/PARSED apps only. Poll
    GET /pipeline/status for the result. scored=0 means nothing pending."""
    def worker() -> dict:
        with get_session() as db:
            succeeded, failed = parse_and_score_pending(db)
        return ScoreResult(succeeded=succeeded, failed=failed).model_dump()

    return try_start_job("score", worker)


@router.post("/rank")
def rank() -> dict:
    """Starts background re-ranking. Poll GET /pipeline/status when done."""
    def worker() -> dict:
        with get_session() as db:
            rank_all(db)
        return {"status": "ok"}

    return try_start_job("rank", worker)


@router.post("/run-all")
def run_all() -> dict:
    """Starts fetch -> score -> rank -> report in the background. Poll
    GET /pipeline/status (do not expect the final counts in this response)."""
    def worker() -> dict:
        with get_session() as db:
            created = fetch_submissions(db)
        with get_session() as db:
            succeeded, failed = parse_and_score_pending(db)
            rank_all(db)
            reports = generate_all_reports(db)
        return PipelineRunResult(
            new_applications=created, scored=succeeded, failed=failed, reports=reports
        ).model_dump()

    return try_start_job("run-all", worker)
