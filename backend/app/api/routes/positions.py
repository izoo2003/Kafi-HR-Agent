"""Read-only endpoints for browsing scored/ranked candidates."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas import CandidateRankingOut, PositionSummaryOut
from app.ranking.ranker import get_ranked_applications, list_positions

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionSummaryOut])
def list_all_positions(db: Session = Depends(get_db)) -> list[PositionSummaryOut]:
    summaries = []
    for position in list_positions(db):
        applications = get_ranked_applications(db, position)
        top = applications[0] if applications else None
        summaries.append(
            PositionSummaryOut(
                position=position,
                candidates_scored=len(applications),
                top_candidate=top.candidate.full_name if top else None,
                top_score=top.score if top else None,
                top_verdict=top.verdict if top else None,
            )
        )
    return summaries


@router.get("/{position}/candidates", response_model=list[CandidateRankingOut])
def list_candidates_for_position(position: str, db: Session = Depends(get_db)) -> list[CandidateRankingOut]:
    applications = get_ranked_applications(db, position)
    if not applications:
        raise HTTPException(status_code=404, detail=f"No scored candidates found for position '{position}'")

    return [
        CandidateRankingOut(
            rank=a.rank_in_position,
            application_id=a.id,
            candidate_name=a.candidate.full_name,
            email=a.candidate.email,
            phone=a.candidate.phone,
            location=a.candidate.location,
            position=a.position_applied,
            score=a.score,
            verdict=a.verdict,
            source=a.source.value,
            status=a.status.value,
            education_summary=a.education_summary,
            experience_summary=a.experience_summary,
            key_strengths=json.loads(a.key_strengths_json) if a.key_strengths_json else [],
            hiring_summary=a.hiring_summary,
            submitted_at=a.submitted_at,
            scored_at=a.scored_at,
        )
        for a in applications
    ]
