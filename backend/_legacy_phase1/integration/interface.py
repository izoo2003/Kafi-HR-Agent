"""Public interface seam for the HR & Admin agent's CV Ranking capability.

This is the ONLY module a future parent/orchestrator (or a sibling agent)
should import from. Internal modules (db, ingestion, scoring, ranking,
reporting) can be refactored freely as long as these typed
request/response shapes and function signatures stay stable.

Nothing here does real cross-agent auth/eventing yet — these are no-op
stubs so the seam exists now and can be wired to the shared orchestrator's
auth context / event bus later without touching call sites.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.db.database import get_session
from app.pipeline import fetch_submissions, generate_all_reports, parse_and_score_pending, rank_all
from app.ranking.ranker import get_ranked_applications, list_positions

AGENT_ID = "hr_admin_agent"
CAPABILITY_NAME = "cv_ranking"


@dataclass(frozen=True)
class AuthContext:
    """Placeholder for identity/permissions passed down from a shared
    orchestrator. Until that exists, `role_matrix_role` is unused and every
    call is treated as authorized locally."""

    caller_agent_id: str | None = None
    role_matrix_role: str | None = None  # ties to the shared user role matrix (scope item 6)


@dataclass(frozen=True)
class CandidateRankingDTO:
    rank: int
    candidate_name: str
    email: str
    position: str
    score: float
    verdict: str
    hiring_summary: str


@dataclass(frozen=True)
class RunPipelineResponse:
    new_applications: int
    scored: int
    failed: int
    report_paths: list[str] = field(default_factory=list)


def run_cv_ranking_pipeline(auth: AuthContext | None = None) -> RunPipelineResponse:
    """Fetch -> score -> rank -> report, in one call. This is what an
    orchestrator would trigger on a schedule or webhook event."""
    with get_session() as session:
        created = fetch_submissions(session)
        succeeded, failed = parse_and_score_pending(session)
        rank_all(session)
        reports = generate_all_reports(session)

    return RunPipelineResponse(
        new_applications=created, scored=succeeded, failed=failed, report_paths=reports
    )


def get_rankings_for_position(position: str, auth: AuthContext | None = None) -> list[CandidateRankingDTO]:
    """Read-only lookup a sibling agent/orchestrator could call to display
    rankings without touching our DB directly."""
    with get_session() as session:
        applications = get_ranked_applications(session, position)
        return [
            CandidateRankingDTO(
                rank=a.rank_in_position or 0,
                candidate_name=a.candidate.full_name,
                email=a.candidate.email,
                position=a.position_applied,
                score=a.score or 0,
                verdict=a.verdict or "",
                hiring_summary=a.hiring_summary or "",
            )
            for a in applications
        ]


def list_open_positions(auth: AuthContext | None = None) -> list[str]:
    with get_session() as session:
        return list_positions(session)


# --- Event hooks (no-ops for now) ---------------------------------------
# When the shared orchestrator/event bus exists, register handlers here,
# e.g. on_new_application_scored(handler) so sibling agents can react
# (notifications agent, dashboard agent, etc.) without this module knowing
# about them.

_event_subscribers: dict[str, list[Callable[[Any], None]]] = {}


def subscribe(event_name: str, handler: Callable[[Any], None]) -> None:
    _event_subscribers.setdefault(event_name, []).append(handler)


def _emit(event_name: str, payload: Any) -> None:
    for handler in _event_subscribers.get(event_name, []):
        handler(payload)
