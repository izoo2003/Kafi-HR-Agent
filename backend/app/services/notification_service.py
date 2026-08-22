"""In-app notification CRUD + KPI reminder generation."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import EntityNotFound
from app.models.employees import Department
from app.models.identity import AgentAccessMatrix, User, UserRole
from app.models.notification import AppNotification
from app.schemas.common import PERMISSION_RANK, AuthContext, PaginatedResponse
from app.schemas.notification import AppNotificationRead
from app.services import kpi_service


def list_for_user(
    db: Session,
    auth: AuthContext,
    *,
    page: int = 1,
    page_size: int = 30,
    unread_only: bool = False,
) -> PaginatedResponse[AppNotificationRead]:
    q = db.query(AppNotification).filter(AppNotification.user_id == auth.user_id)
    if unread_only:
        q = q.filter(AppNotification.read_at.is_(None))
    total = q.count()
    rows = (
        q.order_by(AppNotification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=[AppNotificationRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def unread_count(db: Session, auth: AuthContext) -> int:
    return (
        db.query(AppNotification)
        .filter(AppNotification.user_id == auth.user_id, AppNotification.read_at.is_(None))
        .count()
    )


def mark_read(db: Session, auth: AuthContext, notification_id: int) -> AppNotification:
    row = (
        db.query(AppNotification)
        .filter(AppNotification.id == notification_id, AppNotification.user_id == auth.user_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound("Notification not found")
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        db.flush()
    return row


def mark_all_read(db: Session, auth: AuthContext) -> int:
    rows = (
        db.query(AppNotification)
        .filter(AppNotification.user_id == auth.user_id, AppNotification.read_at.is_(None))
        .all()
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        row.read_at = now
    db.flush()
    return len(rows)


def _users_with_kpi_read(db: Session) -> list[User]:
    role_ids = {
        m.role_id
        for m in db.query(AgentAccessMatrix)
        .filter(
            AgentAccessMatrix.agent_key == "hr_admin",
            AgentAccessMatrix.module_key == "kpi",
        )
        .all()
        if PERMISSION_RANK.get(m.permission, 0) >= PERMISSION_RANK.get("read", 1)
    }
    if not role_ids:
        return []
    user_ids = {
        ur.user_id
        for ur in db.query(UserRole).filter(UserRole.role_id.in_(role_ids)).all()
    }
    if not user_ids:
        return []
    return db.query(User).filter(User.id.in_(user_ids), User.is_active.is_(True)).all()


def _already_sent_today(
    db: Session, *, user_id: int, kind: str, department_id: int, day: date
) -> bool:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    # Compare created_at date loosely — store day in payload and check
    rows = (
        db.query(AppNotification)
        .filter(
            AppNotification.user_id == user_id,
            AppNotification.kind == kind,
            AppNotification.created_at >= start,
        )
        .all()
    )
    for r in rows:
        if (r.payload or {}).get("department_id") == department_id:
            return True
    return False


def create_for_users(
    db: Session,
    *,
    users: list[User],
    title: str,
    body: str,
    kind: str,
    payload: dict | None = None,
) -> int:
    n = 0
    for user in users:
        db.add(
            AppNotification(
                user_id=user.id,
                title=title,
                body=body,
                kind=kind,
                payload=payload,
            )
        )
        n += 1
    db.flush()
    return n


def _current_month_period(today: date | None = None) -> tuple[date, date]:
    from calendar import monthrange

    day = today or date.today()
    period_start = day.replace(day=1)
    period_end = day.replace(day=monthrange(day.year, day.month)[1])
    return period_start, period_end


def run_kpi_incomplete_reminders(db: Session) -> int:
    """18:00 job — departments with incomplete KPI entry coverage for current month."""
    kpi_service.cleanup_duplicate_work_log_definitions(db)
    today = date.today()
    period_start, period_end = _current_month_period(today)

    users = _users_with_kpi_read(db)
    if not users:
        return 0

    created = 0
    departments = db.query(Department).all()
    for dept in departments:
        defs = kpi_service._active_definitions(db, dept.id)  # noqa: SLF001
        if not defs:
            continue
        summary = kpi_service.department_kpi_summary(db, dept.id, period_start, period_end)
        if summary.entries_expected == 0:
            continue
        if summary.completeness >= 0.999:
            continue
        title = f"KPI entries incomplete — {dept.name}"
        body = (
            f"{summary.entries_recorded}/{summary.entries_expected} entries recorded for "
            f"{period_start.isoformat()}–{period_end.isoformat()} "
            f"({round(summary.completeness * 100)}% complete). "
            "Open KPI Dashboard and record actuals."
        )
        payload = {
            "department_id": dept.id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "kind_detail": "incomplete",
        }
        for user in users:
            if _already_sent_today(
                db, user_id=user.id, kind="kpi_incomplete", department_id=dept.id, day=today
            ):
                continue
            db.add(
                AppNotification(
                    user_id=user.id,
                    title=title,
                    body=body,
                    kind="kpi_incomplete",
                    payload=payload,
                )
            )
            created += 1
    db.commit()
    return created


def run_kpi_at_risk_reminders(db: Session) -> int:
    """18:20 job — departments below target / at risk for current month."""
    kpi_service.cleanup_duplicate_work_log_definitions(db)
    today = date.today()
    period_start, period_end = _current_month_period(today)

    users = _users_with_kpi_read(db)
    if not users:
        return 0

    created = 0
    for dept in db.query(Department).all():
        defs = kpi_service._active_definitions(db, dept.id)  # noqa: SLF001
        if not defs:
            continue
        summary = kpi_service.department_kpi_summary(db, dept.id, period_start, period_end)
        if summary.entries_recorded == 0:
            # covered by incomplete job
            continue
        if summary.band == "on_target":
            continue
        title = f"KPI targets {summary.band.replace('_', ' ')} — {dept.name}"
        body = (
            f"Department overall score is {summary.overall_score} "
            f"({summary.band.replace('_', ' ')}) for {period_start.isoformat()}–"
            f"{period_end.isoformat()}. Review the KPI Dashboard."
        )
        payload = {
            "department_id": dept.id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "band": summary.band,
            "kind_detail": "at_risk",
        }
        for user in users:
            if _already_sent_today(
                db, user_id=user.id, kind="kpi_at_risk", department_id=dept.id, day=today
            ):
                continue
            db.add(
                AppNotification(
                    user_id=user.id,
                    title=title,
                    body=body,
                    kind="kpi_at_risk",
                    payload=payload,
                )
            )
            created += 1
    db.commit()
    return created
