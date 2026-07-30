"""Groups scored applications by position and assigns rank order (#1 = best
score) within each position — mirrors the reference report's per-role
ranking table.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Application, ApplicationStatus


def recompute_ranks(session: Session, position: str | None = None) -> None:
    """Recomputes rank_in_position for all scored applications, optionally
    scoped to a single position. Safe to call repeatedly (idempotent)."""
    stmt = select(Application).where(Application.status == ApplicationStatus.SCORED)
    if position:
        stmt = stmt.where(Application.position_applied == position)

    applications = session.execute(stmt).scalars().all()

    by_position: dict[str, list[Application]] = {}
    for app_ in applications:
        by_position.setdefault(app_.position_applied, []).append(app_)

    for _, apps in by_position.items():
        apps.sort(key=lambda a: (a.score or 0), reverse=True)
        for rank, app_ in enumerate(apps, start=1):
            app_.rank_in_position = rank


def get_ranked_applications(session: Session, position: str) -> list[Application]:
    stmt = (
        select(Application)
        .where(Application.position_applied == position, Application.status == ApplicationStatus.SCORED)
        .order_by(Application.rank_in_position.asc())
    )
    return list(session.execute(stmt).scalars().all())


def list_positions(session: Session) -> list[str]:
    stmt = (
        select(Application.position_applied)
        .where(Application.status == ApplicationStatus.SCORED)
        .distinct()
    )
    return [row[0] for row in session.execute(stmt).all()]
