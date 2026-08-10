"""KPI definitions, entries, rollups, period close — FEATURE_KPI.md."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, EntityNotFound, ValidationFailed
from app.integration.event_bus_stub import publish_event
from app.models.employees import Department, Employee
from app.models.kpi import KpiDefinition, KpiEntry
from app.models.system import SystemConfig
from app.schemas.common import AuthContext, PaginatedResponse
from app.core.config import get_settings
from app.schemas.kpi import (
    DepartmentKpiBreakdown,
    DepartmentKpiSummary,
    EmployeeKpiEntrySummary,
    EmployeeKpiSummary,
    KpiAiSuggestRequest,
    KpiAiSuggestResponse,
    KpiDefinitionCreate,
    KpiDefinitionRead,
    KpiDefinitionUpdate,
    KpiEntryCreate,
    KpiEntryRead,
    KpiEntryUpdate,
    MarkPeriodReviewedResponse,
    SeedDefaultsResponse,
)
from app.services import audit_service

Band = Literal["on_target", "at_risk", "below_target"]

OTHER_KPI_NAME = "Other / ad-hoc work"

# (name, description, measurement_unit, target_value, weight) — each pack sums to 1.0
KpiPackItem = tuple[str, str, str, Decimal, float]

_OTHER: KpiPackItem = (
    OTHER_KPI_NAME,
    "Catch-all for typed ad-hoc work described in notes",
    "count",
    Decimal("10"),
    0.10,
)

# Generic fallback when department name is unknown / custom.
GENERIC_KPI_PACK: list[KpiPackItem] = [
    ("Delivery / output", "Work delivered against plan", "count", Decimal("100"), 0.35),
    ("Quality / accuracy", "Quality of deliverables", "%", Decimal("100"), 0.25),
    ("Responsiveness / SLAs", "Timely responses and SLA adherence", "%", Decimal("100"), 0.20),
    (
        "Collaboration / process",
        "Team collaboration and process adherence",
        "score_1_5",
        Decimal("5"),
        0.10,
    ),
    _OTHER,
]

# Department-name → pack (matched case-insensitively). Custom depts fall back to GENERIC.
DEPARTMENT_KPI_PACKS: dict[str, list[KpiPackItem]] = {
    "it": [
        ("Ticket / incident resolution", "Incidents and tickets closed in period", "count", Decimal("40"), 0.30),
        ("System uptime / reliability", "Uptime or reliability against target", "%", Decimal("99"), 0.25),
        ("Response time / SLAs", "SLA / first-response adherence", "%", Decimal("95"), 0.20),
        ("Security & compliance", "Security tasks / compliance checks completed", "score_1_5", Decimal("5"), 0.15),
        _OTHER,
    ],
    "engineering": [
        ("Feature delivery", "Features / stories delivered", "count", Decimal("20"), 0.35),
        ("Code quality / defects", "Quality score or defect-free delivery rate", "%", Decimal("95"), 0.25),
        ("Sprint commitment met", "Committed work completed in sprint/period", "%", Decimal("90"), 0.20),
        ("Code reviews / collaboration", "Review participation and teamwork", "score_1_5", Decimal("5"), 0.10),
        _OTHER,
    ],
    "hr": [
        ("Hiring / time-to-fill", "Open roles filled or hiring milestones hit", "count", Decimal("5"), 0.25),
        ("Employee engagement", "Engagement / satisfaction pulse score", "score_1_5", Decimal("5"), 0.25),
        ("Policy & compliance", "HR policy / compliance tasks completed", "%", Decimal("100"), 0.20),
        ("Training completion", "Required training completed on time", "%", Decimal("95"), 0.20),
        _OTHER,
    ],
    "sales": [
        ("Quota / revenue attainment", "Revenue or quota achievement", "%", Decimal("100"), 0.40),
        ("New clients acquired", "New customers closed", "count", Decimal("10"), 0.25),
        ("Pipeline conversion", "Qualified leads converted", "%", Decimal("30"), 0.15),
        ("Client retention", "Existing-client retention / renewals", "%", Decimal("90"), 0.10),
        _OTHER,
    ],
    "accounting": [
        ("Month-end close on time", "Close completed by target date (score)", "score_1_5", Decimal("5"), 0.30),
        ("Collections / receivables", "Invoices collected vs due", "%", Decimal("95"), 0.25),
        ("Audit readiness / accuracy", "Error-free books / audit readiness", "%", Decimal("100"), 0.20),
        ("Reporting timeliness", "Reports delivered on schedule", "%", Decimal("100"), 0.15),
        _OTHER,
    ],
    "operations": [
        ("On-time delivery", "Jobs / orders delivered on time", "%", Decimal("95"), 0.30),
        ("Process efficiency", "Efficiency / throughput vs plan", "%", Decimal("90"), 0.25),
        ("Quality / error rate", "First-pass quality (higher is better)", "%", Decimal("98"), 0.20),
        ("Cost control", "Operating within budget targets", "%", Decimal("100"), 0.15),
        _OTHER,
    ],
    "digital marketing": [
        ("Leads / campaign results", "Qualified leads or campaign outcomes", "count", Decimal("50"), 0.30),
        ("Content publishing cadence", "Planned content pieces published", "count", Decimal("20"), 0.25),
        ("Engagement / conversion", "Engagement or conversion rate", "%", Decimal("5"), 0.20),
        ("Channel / brand growth", "Follower or reach growth vs target", "%", Decimal("10"), 0.15),
        _OTHER,
    ],
    "graphic design": [
        ("Designs delivered on time", "Assets delivered by deadline", "count", Decimal("25"), 0.35),
        ("Revision / quality score", "Quality after review cycles", "score_1_5", Decimal("5"), 0.25),
        ("Brand guideline adherence", "Work meeting brand standards", "%", Decimal("100"), 0.20),
        ("Stakeholder satisfaction", "Requester satisfaction", "score_1_5", Decimal("5"), 0.10),
        _OTHER,
    ],
    "customer support": [
        ("Ticket resolution rate", "Tickets resolved in period", "%", Decimal("95"), 0.30),
        ("First response time", "First-response SLA met", "%", Decimal("90"), 0.25),
        ("CSAT / satisfaction", "Customer satisfaction score", "score_1_5", Decimal("5"), 0.25),
        ("Escalation control", "Resolved without escalation", "%", Decimal("85"), 0.10),
        _OTHER,
    ],
    "general": GENERIC_KPI_PACK,
}

# Back-compat alias used by tests / imports
DEFAULT_KPI_PACK = GENERIC_KPI_PACK


def _kpi_pack_for_department(department_name: str) -> list[KpiPackItem]:
    key = (department_name or "").strip().lower()
    return DEPARTMENT_KPI_PACKS.get(key, GENERIC_KPI_PACK)


def _score_cap(db: Session) -> float:
    row = db.query(SystemConfig).filter_by(key="kpi.score_cap").one_or_none()
    if row and isinstance(row.value, (int, float)):
        return float(row.value)
    if row and isinstance(row.value, dict) and "cap" in row.value:
        return float(row.value["cap"])
    return 1.5


def _score_bands(db: Session) -> tuple[float, float]:
    """Returns (on_target_min, at_risk_min)."""
    row = db.query(SystemConfig).filter_by(key="kpi.score_bands").one_or_none()
    on_target = 90.0
    at_risk = 70.0
    if row and isinstance(row.value, dict):
        on_target = float(row.value.get("on_target_min", on_target))
        at_risk = float(row.value.get("at_risk_min", at_risk))
    return on_target, at_risk


def score_band(score: float, db: Session) -> Band:
    on_target, at_risk = _score_bands(db)
    if score >= on_target:
        return "on_target"
    if score >= at_risk:
        return "at_risk"
    return "below_target"


def compute_entry_score(actual: Decimal, target: Decimal, db: Session) -> float:
    if target == 0:
        return 0.0
    normalized = float(actual) / float(target)
    cap = _score_cap(db)
    normalized = min(normalized, cap)
    return round(normalized * 100.0, 2)


def _active_definitions(db: Session, department_id: int) -> list[KpiDefinition]:
    return (
        db.query(KpiDefinition)
        .filter(
            KpiDefinition.department_id == department_id,
            KpiDefinition.is_archived.is_(False),
        )
        .order_by(KpiDefinition.id)
        .all()
    )


def _weight_sum(db: Session, department_id: int) -> float:
    return sum(float(d.weight or 0) for d in _active_definitions(db, department_id))


def _validate_weights_not_over(db: Session, department_id: int) -> None:
    total = _weight_sum(db, department_id)
    if total > 1.0 + 0.001:
        raise ValidationFailed(
            f"Active KPI weights for this department cannot exceed 1.0 (got {total:.4f})",
            details={"weight_sum": total},
        )


def _require_weights_complete(db: Session, department_id: int) -> None:
    defs = _active_definitions(db, department_id)
    total = sum(float(d.weight or 0) for d in defs)
    if not defs or abs(total - 1.0) > 0.001:
        raise ValidationFailed(
            f"Active KPI weights for this department must sum to 1.0 before recording (got {total:.4f})",
            details={"weight_sum": total},
        )


def ensure_kpi_config(db: Session) -> None:
    _ensure_kpi_schema(db)
    if db.query(SystemConfig).filter_by(key="kpi.score_cap").one_or_none() is None:
        db.add(SystemConfig(key="kpi.score_cap", value={"cap": 1.5}))
    if db.query(SystemConfig).filter_by(key="kpi.score_bands").one_or_none() is None:
        db.add(
            SystemConfig(
                key="kpi.score_bands",
                value={"on_target_min": 90, "at_risk_min": 70},
            )
        )


def _ensure_kpi_schema(db: Session) -> None:
    """Dev SQLite: add columns/indexes create_all won't retrofit on existing tables."""
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "sqlite":
        return
    cols = {row[1] for row in db.execute(text("PRAGMA table_info(kpi_definitions)")).fetchall()}
    if cols and "is_archived" not in cols:
        db.execute(
            text("ALTER TABLE kpi_definitions ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT 0")
        )
    indexes = {row[1] for row in db.execute(text("PRAGMA index_list(kpi_entries)")).fetchall()}
    if "uq_kpi_entry_period" not in indexes:
        try:
            db.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_kpi_entry_period "
                    "ON kpi_entries (kpi_definition_id, employee_id, period_start, period_end)"
                )
            )
        except Exception:
            pass  # duplicate rows would block; leave for manual cleanup



# --- Definitions ---


def list_definitions(
    db: Session,
    *,
    department_id: int | None = None,
    include_archived: bool = False,
) -> list[KpiDefinition]:
    q = db.query(KpiDefinition)
    if department_id is not None:
        q = q.filter(KpiDefinition.department_id == department_id)
    if not include_archived:
        q = q.filter(KpiDefinition.is_archived.is_(False))
    return q.order_by(KpiDefinition.department_id, KpiDefinition.id).all()


def create_definition(
    db: Session, auth: AuthContext, payload: KpiDefinitionCreate
) -> KpiDefinition:
    if db.query(Department).filter(Department.id == payload.department_id).one_or_none() is None:
        raise ValidationFailed("department_id does not exist")
    row = KpiDefinition(**payload.model_dump(), is_archived=False)
    db.add(row)
    db.flush()
    _validate_weights_not_over(db, payload.department_id)
    audit_service.log_from_auth(
        db,
        auth,
        action="kpi_definition.created",
        entity_type="kpi_definition",
        entity_id=row.id,
        after_state={"name": row.name, "weight": row.weight, "department_id": row.department_id},
    )
    return row


def update_definition(
    db: Session, auth: AuthContext, definition_id: int, payload: KpiDefinitionUpdate
) -> KpiDefinition:
    row = db.query(KpiDefinition).filter(KpiDefinition.id == definition_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"KPI definition {definition_id} not found")
    before = {"name": row.name, "weight": row.weight, "target_value": str(row.target_value)}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.flush()
    _validate_weights_not_over(db, row.department_id)
    after = {
        k: str(v) if isinstance(v, Decimal) else v for k, v in data.items()
    }
    audit_service.log_from_auth(
        db,
        auth,
        action="kpi_definition.updated",
        entity_type="kpi_definition",
        entity_id=row.id,
        before_state=before,
        after_state=after,
    )
    return row


def archive_definition(db: Session, auth: AuthContext, definition_id: int) -> KpiDefinition:
    row = db.query(KpiDefinition).filter(KpiDefinition.id == definition_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"KPI definition {definition_id} not found")
    row.is_archived = True
    db.flush()
    # remaining weights may no longer sum to 1 — that's ok until HR rebalances; warn via validation on next create
    audit_service.log_from_auth(
        db,
        auth,
        action="kpi_definition.updated",
        entity_type="kpi_definition",
        entity_id=row.id,
        after_state={"is_archived": True},
    )
    return row


def seed_default_definitions(
    db: Session, auth: AuthContext, department_id: int
) -> SeedDefaultsResponse:
    """Idempotent department-specific pack. Skips names that already exist."""
    dept = db.query(Department).filter(Department.id == department_id).one_or_none()
    if dept is None:
        raise EntityNotFound(f"Department {department_id} not found")

    pack = _kpi_pack_for_department(dept.name)
    existing = _active_definitions(db, department_id)
    existing_names = {d.name.strip().lower() for d in existing}
    created: list[KpiDefinition] = []
    skipped: list[str] = []

    # Only fill missing named defaults when they fit under remaining weight budget.
    remaining = max(0.0, 1.0 - _weight_sum(db, department_id))

    for name, description, unit, target, weight in pack:
        if name.strip().lower() in existing_names:
            skipped.append(name)
            continue
        if weight > remaining + 0.001:
            skipped.append(name)
            continue
        row = KpiDefinition(
            department_id=department_id,
            name=name,
            description=description,
            measurement_unit=unit,
            target_value=target,
            weight=weight,
            review_period="monthly",
            is_archived=False,
        )
        db.add(row)
        db.flush()
        remaining -= weight
        created.append(row)
        audit_service.log_from_auth(
            db,
            auth,
            action="kpi_definition.created",
            entity_type="kpi_definition",
            entity_id=row.id,
            after_state={
                "name": name,
                "weight": weight,
                "seeded": True,
                "department": dept.name,
            },
        )

    if not created and not existing:
        raise ValidationFailed(f"Could not seed default KPIs for {dept.name}")

    if not created:
        msg = (
            f"No new defaults added for {dept.name} — "
            "existing KPIs already cover these names or the weight budget (1.0). "
            "Add custom KPIs manually below, or archive some first."
        )
    else:
        msg = (
            f"Seeded {len(created)} {dept.name}-specific KPI(s)"
            + (f"; skipped {len(skipped)} existing/over-budget" if skipped else "")
            + ". You can still add custom KPIs manually."
        )

    return SeedDefaultsResponse(
        message=msg,
        created=[KpiDefinitionRead.model_validate(r) for r in created],
        skipped_existing=skipped,
    )


def ai_suggest_entry(
    db: Session, auth: AuthContext, payload: KpiAiSuggestRequest
) -> KpiAiSuggestResponse:
    """Gemini maps free-text work done → best KPI definition + suggested actual (no write)."""
    _ = auth
    defs = _active_definitions(db, payload.department_id)
    if not defs:
        raise ValidationFailed(
            "No active KPI definitions for this department — seed defaults or create KPIs first"
        )
    emp = db.query(Employee).filter(Employee.id == payload.employee_id).one_or_none()
    if emp is None or emp.department_id != payload.department_id:
        raise ValidationFailed("Employee must belong to the selected department")

    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key or api_key.startswith("your_"):
        # Deterministic fallback: Other KPI or first def; crude count of lines/sentences
        other = next((d for d in defs if d.name == OTHER_KPI_NAME), defs[-1])
        approx = float(min(max(payload.text.count("\n") + 1, 1), float(other.target_value or 10)))
        return KpiAiSuggestResponse(
            kpi_definition_id=other.id,
            actual_value=approx,
            reasoning="Gemini not configured — suggested Other / ad-hoc with a rough count from the text.",
        )

    import json
    import re

    import google.generativeai as genai

    catalog = [
        {
            "id": d.id,
            "name": d.name,
            "unit": d.measurement_unit,
            "target": float(d.target_value or 0),
        }
        for d in defs
    ]
    prompt = f"""You help HR map free-text work into one existing KPI definition and an actual_value.

Department KPI catalog (JSON):
{json.dumps(catalog)}

Work description from employee:
---
{payload.text.strip()}
---

Period: {payload.period_start} to {payload.period_end}

Respond with STRICT JSON only:
{{"kpi_definition_id": <id from catalog>, "actual_value": <number>, "reasoning": "<short>"}}

Rules:
- kpi_definition_id MUST be one of the catalog ids.
- Prefer a specific KPI over "Other / ad-hoc work" when the text clearly matches.
- actual_value should be realistic vs that KPI's target/unit (e.g. % 0-150, score_1_5 1-5, counts >= 0).
"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(settings.gemini_model or "gemini-flash-latest")
        response = model.generate_content(prompt)
        raw = (response.text or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        raise ValidationFailed(f"AI suggest failed: {exc}") from exc

    kid = int(data.get("kpi_definition_id") or 0)
    if kid not in {d.id for d in defs}:
        raise ValidationFailed("AI returned an unknown kpi_definition_id")
    actual = float(data.get("actual_value") or 0)
    if actual < 0:
        actual = 0.0
    return KpiAiSuggestResponse(
        kpi_definition_id=kid,
        actual_value=actual,
        reasoning=str(data.get("reasoning") or "AI suggestion"),
    )


# --- Entries ---


def list_entries(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    employee_id: int | None = None,
    department_id: int | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> PaginatedResponse[KpiEntryRead]:
    q = db.query(KpiEntry).join(KpiDefinition, KpiDefinition.id == KpiEntry.kpi_definition_id)
    if employee_id is not None:
        q = q.filter(KpiEntry.employee_id == employee_id)
    if department_id is not None:
        q = q.filter(KpiDefinition.department_id == department_id)
    if period_start is not None:
        q = q.filter(KpiEntry.period_start >= period_start)
    if period_end is not None:
        q = q.filter(KpiEntry.period_end <= period_end)
    total = q.count()
    rows = q.order_by(KpiEntry.period_start.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[KpiEntryRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_entry(db: Session, auth: AuthContext, payload: KpiEntryCreate) -> KpiEntry:
    definition = (
        db.query(KpiDefinition).filter(KpiDefinition.id == payload.kpi_definition_id).one_or_none()
    )
    if definition is None or definition.is_archived:
        raise EntityNotFound("KPI definition not found or archived")
    if payload.period_end < payload.period_start:
        raise ValidationFailed("period_end must be on or after period_start")
    emp = db.query(Employee).filter(Employee.id == payload.employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound("Employee not found")
    if emp.department_id != definition.department_id:
        raise ValidationFailed("Employee must belong to the KPI's department")
    _require_weights_complete(db, definition.department_id)

    existing = (
        db.query(KpiEntry)
        .filter(
            KpiEntry.kpi_definition_id == payload.kpi_definition_id,
            KpiEntry.employee_id == payload.employee_id,
            KpiEntry.period_start == payload.period_start,
            KpiEntry.period_end == payload.period_end,
        )
        .one_or_none()
    )
    if existing:
        raise ConflictError(
            "KPI entry already exists for this employee/definition/period — PATCH to correct it",
            details={"existing_id": existing.id},
        )

    target = definition.target_value or Decimal("0")
    score = compute_entry_score(payload.actual_value, target, db)
    row = KpiEntry(
        kpi_definition_id=payload.kpi_definition_id,
        employee_id=payload.employee_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        actual_value=payload.actual_value,
        score=score,
        recorded_by=auth.user_id,
        notes=payload.notes,
    )
    db.add(row)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="kpi_entry.recorded",
        entity_type="kpi_entry",
        entity_id=row.id,
        after_state={
            "employee_id": row.employee_id,
            "actual_value": str(row.actual_value),
            "score": row.score,
        },
    )
    return row


def update_entry(
    db: Session, auth: AuthContext, entry_id: int, payload: KpiEntryUpdate
) -> KpiEntry:
    row = db.query(KpiEntry).filter(KpiEntry.id == entry_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"KPI entry {entry_id} not found")
    definition = db.query(KpiDefinition).filter(KpiDefinition.id == row.kpi_definition_id).one()
    before = {"actual_value": str(row.actual_value), "score": row.score}
    data = payload.model_dump(exclude_unset=True)
    if "actual_value" in data and data["actual_value"] is not None:
        row.actual_value = data["actual_value"]
        row.score = compute_entry_score(
            row.actual_value, definition.target_value or Decimal("0"), db
        )
    if "notes" in data:
        row.notes = data["notes"]
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="kpi_entry.corrected",
        entity_type="kpi_entry",
        entity_id=row.id,
        before_state=before,
        after_state={"actual_value": str(row.actual_value), "score": row.score},
    )
    return row


# --- Rollups ---


def _employee_in_period(emp: Employee, period_start: date, period_end: date) -> bool:
    """Majority-of-period tenure check for completeness."""
    joined = emp.date_joined or period_start
    exited = emp.date_exited or period_end
    if joined > period_end or exited < period_start:
        return False
    overlap_start = max(joined, period_start)
    overlap_end = min(exited, period_end)
    overlap_days = (overlap_end - overlap_start).days + 1
    period_days = (period_end - period_start).days + 1
    return overlap_days >= (period_days / 2)


def employee_kpi_summary(
    db: Session,
    employee_id: int,
    period_start: date,
    period_end: date,
) -> EmployeeKpiSummary:
    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")

    definitions = _active_definitions(db, emp.department_id)
    entries = (
        db.query(KpiEntry)
        .filter(
            KpiEntry.employee_id == employee_id,
            KpiEntry.period_start == period_start,
            KpiEntry.period_end == period_end,
        )
        .all()
    )
    by_def = {e.kpi_definition_id: e for e in entries}

    summary_entries: list[EmployeeKpiEntrySummary] = []
    overall = 0.0
    for d in definitions:
        e = by_def.get(d.id)
        if e is None or e.score is None:
            continue
        w = float(d.weight or 0)
        summary_entries.append(
            EmployeeKpiEntrySummary(
                kpi_definition_id=d.id,
                name=d.name,
                target=float(d.target_value or 0),
                actual=float(e.actual_value),
                score=float(e.score),
                weight=w,
                band=score_band(float(e.score), db),
            )
        )
        overall += float(e.score) * w

    overall_score = round(overall, 2)
    return EmployeeKpiSummary(
        employee_id=employee_id,
        period_start=period_start,
        period_end=period_end,
        overall_score=overall_score,
        band=score_band(overall_score, db),
        entries=summary_entries,
    )


def department_kpi_summary(
    db: Session,
    department_id: int,
    period_start: date,
    period_end: date,
) -> DepartmentKpiSummary:
    if db.query(Department).filter(Department.id == department_id).one_or_none() is None:
        raise EntityNotFound(f"Department {department_id} not found")

    definitions = _active_definitions(db, department_id)
    employees = (
        db.query(Employee)
        .filter(Employee.department_id == department_id, Employee.status == "active")
        .all()
    )
    eligible = [e for e in employees if _employee_in_period(e, period_start, period_end)]

    entries_expected = len(eligible) * len(definitions)
    recorded = 0
    if definitions and eligible:
        active_ids = [d.id for d in definitions]
        recorded = (
            db.query(KpiEntry)
            .filter(
                KpiEntry.kpi_definition_id.in_(active_ids),
                KpiEntry.period_start == period_start,
                KpiEntry.period_end == period_end,
                KpiEntry.employee_id.in_([e.id for e in eligible]),
            )
            .count()
        )

    emp_summaries = [
        employee_kpi_summary(db, e.id, period_start, period_end) for e in eligible
    ]
    # only include employees who have at least one entry for display average
    with_scores = [s for s in emp_summaries if s.entries]
    overall = (
        round(sum(s.overall_score for s in with_scores) / len(with_scores), 2)
        if with_scores
        else 0.0
    )

    breakdown: list[DepartmentKpiBreakdown] = []
    for d in definitions:
        scores = [
            next((x.score for x in s.entries if x.kpi_definition_id == d.id), None)
            for s in with_scores
        ]
        scores_f = [float(x) for x in scores if x is not None]
        avg = round(sum(scores_f) / len(scores_f), 2) if scores_f else 0.0
        breakdown.append(
            DepartmentKpiBreakdown(
                kpi_definition_id=d.id,
                name=d.name,
                average_score=avg,
                weight=float(d.weight or 0),
                band=score_band(avg, db),
            )
        )
    breakdown.sort(key=lambda b: b.average_score)  # weakest first — needs attention

    completeness = (recorded / entries_expected) if entries_expected else 1.0
    return DepartmentKpiSummary(
        department_id=department_id,
        period_start=period_start,
        period_end=period_end,
        overall_score=overall,
        band=score_band(overall, db),
        entries_recorded=recorded,
        entries_expected=entries_expected,
        completeness=round(completeness, 4),
        employees=emp_summaries,
        kpi_breakdown=breakdown,
    )


def mark_period_reviewed(
    db: Session,
    auth: AuthContext,
    department_id: int,
    period_start: date,
    period_end: date,
) -> MarkPeriodReviewedResponse:
    summary = department_kpi_summary(db, department_id, period_start, period_end)
    publish_event(
        "hr_admin.kpi.period_closed",
        {
            "department_id": department_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "overall_score": summary.overall_score,
            "completeness": summary.completeness,
        },
    )
    audit_service.log_from_auth(
        db,
        auth,
        action="kpi.period_marked_reviewed",
        entity_type="department",
        entity_id=department_id,
        after_state={
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "completeness": summary.completeness,
        },
    )
    return MarkPeriodReviewedResponse(
        message="Period marked reviewed; hr_admin.kpi.period_closed emitted.",
        department_id=department_id,
        period_start=period_start,
        period_end=period_end,
    )
