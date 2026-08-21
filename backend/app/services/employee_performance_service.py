"""Employee Development — monthly performance score (/10) + AI summary."""
from __future__ import annotations

import calendar
import logging
from calendar import month_name
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleViolation, EntityNotFound, PermissionDenied
from app.core.gemini_client import generate_content_with_fallback
from app.core.self_service import is_self_service, own_employee_id
from app.models.employees import Employee
from app.models.kpi import EmployeeMonthlyPerformance, KpiDefinition, KpiEntry
from app.schemas.common import AuthContext
from app.schemas.employee_performance import (
    EmployeePerformanceAiSummaryResponse,
    EmployeePerformanceRead,
    MonthlyPerformanceHistoryItem,
    PerformanceKpiEntryRead,
)
from app.services import audit_service

logger = logging.getLogger(__name__)


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _period_label(year: int, month: int) -> str:
    return f"{month_name[month]} {year}"


def _is_past_month(year: int, month: int, today: date | None = None) -> bool:
    today = today or date.today()
    return (year, month) < (today.year, today.month)


def _is_current_month(year: int, month: int, today: date | None = None) -> bool:
    today = today or date.today()
    return year == today.year and month == today.month


def _guard_employee_access(auth: AuthContext, employee_id: int) -> None:
    if is_self_service(auth):
        own = own_employee_id(auth)
        if own is None or own != employee_id:
            raise PermissionDenied("You can only view your own performance")


def _entries_for_month(
    db: Session, employee_id: int, year: int, month: int
) -> list[tuple[KpiEntry, KpiDefinition]]:
    start, end = _month_bounds(year, month)
    rows = (
        db.query(KpiEntry, KpiDefinition)
        .join(KpiDefinition, KpiEntry.kpi_definition_id == KpiDefinition.id)
        .filter(
            KpiEntry.employee_id == employee_id,
            KpiEntry.period_start <= end,
            KpiEntry.period_end >= start,
        )
        .order_by(KpiEntry.period_start.desc(), KpiEntry.id.desc())
        .all()
    )
    return list(rows)


def compute_month_score(
    db: Session, employee_id: int, year: int, month: int
) -> tuple[float, float | None, int, list[tuple[KpiEntry, KpiDefinition]]]:
    """Weighted average of entry scores → overall_pct, then /10 capped at 10."""
    pairs = _entries_for_month(db, employee_id, year, month)
    if not pairs:
        return 0.0, None, 0, pairs

    weighted_sum = 0.0
    weight_total = 0.0
    for entry, definition in pairs:
        if entry.score is None:
            continue
        w = float(definition.weight) if definition.weight is not None else 1.0
        if w <= 0:
            continue
        weighted_sum += float(entry.score) * w
        weight_total += w

    if weight_total <= 0:
        # Equal weight among scored entries
        scores = [float(e.score) for e, _ in pairs if e.score is not None]
        if not scores:
            return 0.0, None, len(pairs), pairs
        overall_pct = sum(scores) / len(scores)
    else:
        overall_pct = weighted_sum / weight_total

    score_out_of_10 = min(10.0, round(overall_pct / 10.0, 2))
    return score_out_of_10, round(overall_pct, 2), len(pairs), pairs


def _get_snapshot(
    db: Session, employee_id: int, year: int, month: int
) -> EmployeeMonthlyPerformance | None:
    return (
        db.query(EmployeeMonthlyPerformance)
        .filter(
            EmployeeMonthlyPerformance.employee_id == employee_id,
            EmployeeMonthlyPerformance.period_year == year,
            EmployeeMonthlyPerformance.period_month == month,
        )
        .one_or_none()
    )


def finalize_month_if_needed(
    db: Session, employee_id: int, year: int, month: int
) -> EmployeeMonthlyPerformance | None:
    """If the month is fully past and has entries, ensure a snapshot row exists."""
    if not _is_past_month(year, month):
        return _get_snapshot(db, employee_id, year, month)

    existing = _get_snapshot(db, employee_id, year, month)
    if existing is not None:
        return existing

    score, overall_pct, count, _ = compute_month_score(db, employee_id, year, month)
    if count == 0:
        return None

    row = EmployeeMonthlyPerformance(
        employee_id=employee_id,
        period_year=year,
        period_month=month,
        score_out_of_10=Decimal(str(score)),
        overall_pct=overall_pct,
        entries_count=count,
        finalized_at=datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    return row


def _finalize_prior_months(db: Session, employee_id: int, year: int, month: int) -> None:
    """When viewing a month, also close any older months that still lack snapshots."""
    today = date.today()
    # Walk back up to 24 months from the viewed period (or today)
    y, m = today.year, today.month
    for _ in range(24):
        # previous month
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        if (y, m) >= (year, month) and not _is_past_month(y, m, today):
            continue
        if _is_past_month(y, m, today):
            finalize_month_if_needed(db, employee_id, y, m)


def list_monthly_history(
    db: Session, employee_id: int
) -> list[MonthlyPerformanceHistoryItem]:
    rows = (
        db.query(EmployeeMonthlyPerformance)
        .filter(EmployeeMonthlyPerformance.employee_id == employee_id)
        .order_by(
            EmployeeMonthlyPerformance.period_year.desc(),
            EmployeeMonthlyPerformance.period_month.desc(),
        )
        .all()
    )
    return [
        MonthlyPerformanceHistoryItem(
            period_year=r.period_year,
            period_month=r.period_month,
            label=_period_label(r.period_year, r.period_month),
            score_out_of_10=float(r.score_out_of_10),
            entries_count=r.entries_count,
            finalized=True,
            ai_summary=r.ai_summary,
        )
        for r in rows
    ]


def get_employee_performance(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int,
    period_year: int,
    period_month: int,
) -> EmployeePerformanceRead:
    _guard_employee_access(auth, employee_id)
    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")

    _finalize_prior_months(db, employee_id, period_year, period_month)
    snapshot = finalize_month_if_needed(db, employee_id, period_year, period_month)

    score, overall_pct, count, pairs = compute_month_score(
        db, employee_id, period_year, period_month
    )
    is_current = _is_current_month(period_year, period_month)
    is_finalized = snapshot is not None and _is_past_month(period_year, period_month)

    if is_finalized and snapshot is not None:
        score = float(snapshot.score_out_of_10)
        overall_pct = snapshot.overall_pct
        count = snapshot.entries_count
        ai_summary = snapshot.ai_summary
    else:
        # Live current (or future empty) month — still refresh live compute
        ai_summary = snapshot.ai_summary if snapshot else None

    entries = [
        PerformanceKpiEntryRead(
            id=entry.id,
            kpi_definition_id=definition.id,
            kpi_name=definition.name,
            measurement_unit=definition.measurement_unit,
            target_value=definition.target_value,
            weight=definition.weight,
            period_start=entry.period_start,
            period_end=entry.period_end,
            actual_value=entry.actual_value,
            score=entry.score,
            notes=entry.notes,
            created_at=entry.created_at,
        )
        for entry, definition in pairs
    ]

    db.commit()

    return EmployeePerformanceRead(
        employee_id=emp.id,
        employee_name=emp.full_name,
        employee_code=emp.employee_code,
        period_year=period_year,
        period_month=period_month,
        period_label=_period_label(period_year, period_month),
        is_current_month=is_current,
        is_finalized=is_finalized,
        score_out_of_10=score,
        overall_pct=overall_pct,
        entries_count=count,
        entries=entries,
        history=list_monthly_history(db, employee_id),
        ai_summary=ai_summary,
    )


def generate_performance_ai_summary(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int,
    period_year: int,
    period_month: int,
    settings: Settings | None = None,
) -> EmployeePerformanceAiSummaryResponse:
    _guard_employee_access(auth, employee_id)
    settings = settings or get_settings()
    api_keys = settings.resolved_gemini_performance_api_keys()
    if not api_keys:
        raise BusinessRuleViolation(
            "Performance AI summary is not configured. Set GEMINI_PERFORMANCE_API_KEY "
            "(or GEMINI_API_KEY as fallback)."
        )

    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")

    snapshot = finalize_month_if_needed(db, employee_id, period_year, period_month)
    score, overall_pct, count, pairs = compute_month_score(
        db, employee_id, period_year, period_month
    )
    if snapshot is not None and _is_past_month(period_year, period_month):
        score = float(snapshot.score_out_of_10)
        overall_pct = snapshot.overall_pct
        count = snapshot.entries_count

    label = _period_label(period_year, period_month)
    lines = [
        f"Employee: {emp.full_name} ({emp.employee_code})",
        f"Period: {label}",
        f"Score out of 10: {score}",
        f"Overall achievement %: {overall_pct if overall_pct is not None else 'n/a'}",
        f"KPI entries logged: {count}",
        "Logged KPIs:",
    ]
    for entry, definition in pairs[:40]:
        lines.append(
            f"- {definition.name}: actual={entry.actual_value}, "
            f"target={definition.target_value}, score%={entry.score}, "
            f"notes={(entry.notes or '')[:200]}"
        )
    facts = "\n".join(lines)

    prompt = f"""You are an HR performance coach for Kafi Commodities.
Write a clear, professional monthly performance summary for this employee.

Use ONLY the facts below. Do not invent KPIs or scores.
Explain how good or weak the month was relative to the /10 score, cite specific KPIs when helpful,
and end with 2–3 short coaching bullets (strengths / improvements).

Facts:
{facts}

Tone: calm, precise, constructive. Plain text, no markdown tables. 3–6 short paragraphs max.
"""

    try:
        response = generate_content_with_fallback(
            prompt=prompt,
            api_keys=api_keys,
            models=settings.resolved_gemini_performance_models(),
            pool_id="employee_performance",
        )
        text = (getattr(response, "text", None) or "").strip()
    except Exception as exc:
        logger.exception("Performance AI summary failed")
        raise BusinessRuleViolation(f"Could not generate performance AI summary: {exc}") from exc

    if not text:
        raise BusinessRuleViolation("Performance AI summary returned empty text")

    # Persist on snapshot for past months; for current month upsert a soft row so summary sticks
    row = snapshot or _get_snapshot(db, employee_id, period_year, period_month)
    if row is None:
        row = EmployeeMonthlyPerformance(
            employee_id=employee_id,
            period_year=period_year,
            period_month=period_month,
            score_out_of_10=Decimal(str(score)),
            overall_pct=overall_pct,
            entries_count=count,
            finalized_at=datetime.now(UTC) if _is_past_month(period_year, period_month) else None,
        )
        db.add(row)
    else:
        # Keep live score fresh on current month when regenerating
        if not _is_past_month(period_year, period_month):
            row.score_out_of_10 = Decimal(str(score))
            row.overall_pct = overall_pct
            row.entries_count = count
    row.ai_summary = text
    db.flush()

    audit_service.log_from_auth(
        db,
        auth,
        action="employee_performance.ai_summary",
        entity_type="employee_monthly_performance",
        entity_id=row.id,
        after_state={
            "employee_id": employee_id,
            "period_year": period_year,
            "period_month": period_month,
            "score_out_of_10": str(score),
        },
    )
    db.commit()

    return EmployeePerformanceAiSummaryResponse(
        employee_id=employee_id,
        period_year=period_year,
        period_month=period_month,
        score_out_of_10=score,
        ai_summary=text,
    )
