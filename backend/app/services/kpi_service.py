"""KPI definitions, entries, rollups, period close — FEATURE_KPI.md."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.core.self_service import is_self_service, own_employee_id
from app.core.exceptions import ConflictError, EntityNotFound, PermissionDenied, ValidationFailed
from app.integration.event_bus_stub import publish_event
from app.models.employees import Department, Employee
from app.models.kpi import KpiDefinition, KpiEntry
from app.models.system import SystemConfig
from app.schemas.common import AuthContext, PaginatedResponse
from app.core.config import get_settings
from app.schemas.kpi import (
    DepartmentEmployeeKpiSummary,
    DepartmentKpiSummary,
    EmployeeWorkItem,
    EmployeeKpiSummary,
    GlobalDepartmentKpiSummary,
    GlobalKpiSummary,
    KpiAiSuggestRequest,
    KpiAiSuggestResponse,
    KpiWorkSubmissionCreate,
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

Band = Literal["on_target", "at_risk", "below_target", "complete"]

OTHER_KPI_NAME = "Other / ad-hoc work"
WORK_LOG_KPI_NAME = "Work submission"
WORK_LOG_TARGET = Decimal("10")
WORK_ENTRY_SEPARATOR = "\n\n---\n\n"
SELF_SERVICE_POINTS_PER_ENTRY = 1.0

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


def work_log_band(score: float) -> Band:
    """Self-service period rating on a 0–10 scale."""
    if score >= 10.0:
        return "complete"
    if score >= 6.0:
        return "on_target"
    return "below_target"


def _is_work_log_definition(defn: KpiDefinition) -> bool:
    return (defn.name or "").strip() == WORK_LOG_KPI_NAME


def _ensure_work_log_definition(db: Session, department_id: int) -> KpiDefinition:
    row = (
        db.query(KpiDefinition)
        .filter(
            KpiDefinition.department_id == department_id,
            KpiDefinition.owner_employee_id.is_(None),
            KpiDefinition.name == WORK_LOG_KPI_NAME,
            KpiDefinition.is_archived.is_(False),
        )
        .one_or_none()
    )
    if row is not None:
        return row
    row = KpiDefinition(
        department_id=department_id,
        name=WORK_LOG_KPI_NAME,
        description="Employee work done this period (self-service submissions)",
        measurement_unit="score_1_10",
        target_value=WORK_LOG_TARGET,
        weight=0.0,
        review_period="monthly",
    )
    db.add(row)
    db.flush()
    return row


def compute_entry_score(actual: Decimal, target: Decimal, db: Session) -> float:
    if target == 0:
        return 0.0
    normalized = float(actual) / float(target)
    cap = _score_cap(db)
    normalized = min(normalized, cap)
    return round(normalized * 100.0, 2)


def _active_definitions(db: Session, department_id: int) -> list[KpiDefinition]:
    """Department-owned KPIs only (excludes personal / self-service KPIs)."""
    return (
        db.query(KpiDefinition)
        .filter(
            KpiDefinition.department_id == department_id,
            KpiDefinition.is_archived.is_(False),
            KpiDefinition.owner_employee_id.is_(None),
        )
        .order_by(KpiDefinition.id)
        .all()
    )


def _personal_definitions(db: Session, employee_id: int) -> list[KpiDefinition]:
    return (
        db.query(KpiDefinition)
        .filter(
            KpiDefinition.owner_employee_id == employee_id,
            KpiDefinition.is_archived.is_(False),
        )
        .order_by(KpiDefinition.id)
        .all()
    )


def _personal_weight_sum(db: Session, employee_id: int) -> float:
    return sum(float(d.weight or 0) for d in _personal_definitions(db, employee_id))


def _validate_personal_weights_not_over(db: Session, employee_id: int) -> None:
    total = _personal_weight_sum(db, employee_id)
    if total > 1.0 + 0.001:
        raise ValidationFailed(
            f"Your personal KPI weights cannot exceed 1.0 (got {total:.4f})",
            details={"weight_sum": total},
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
    auth: AuthContext,
    *,
    department_id: int | None = None,
    include_archived: bool = False,
) -> list[KpiDefinition]:
    q = db.query(KpiDefinition)
    if not include_archived:
        q = q.filter(KpiDefinition.is_archived.is_(False))

    if is_self_service(auth):
        emp = db.query(Employee).filter(Employee.id == auth.linked_employee_id).one()
        q = q.filter(
            or_(
                KpiDefinition.owner_employee_id == emp.id,
                and_(
                    KpiDefinition.owner_employee_id.is_(None),
                    KpiDefinition.department_id == emp.department_id,
                ),
            )
        )
    else:
        q = q.filter(KpiDefinition.owner_employee_id.is_(None))
        if department_id is not None:
            q = q.filter(KpiDefinition.department_id == department_id)
    return q.order_by(KpiDefinition.department_id, KpiDefinition.id).all()


def create_definition(
    db: Session, auth: AuthContext, payload: KpiDefinitionCreate
) -> KpiDefinition:
    department_id = payload.department_id
    owner_employee_id: int | None = None
    if is_self_service(auth):
        emp = db.query(Employee).filter(Employee.id == auth.linked_employee_id).one()
        department_id = emp.department_id
        owner_employee_id = emp.id
    elif department_id is None:
        raise ValidationFailed("department_id is required")
    elif db.query(Department).filter(Department.id == department_id).one_or_none() is None:
        raise ValidationFailed("department_id does not exist")

    data = payload.model_dump()
    data["department_id"] = department_id
    row = KpiDefinition(
        **data,
        owner_employee_id=owner_employee_id,
        is_archived=False,
    )
    db.add(row)
    db.flush()
    if owner_employee_id is not None:
        _validate_personal_weights_not_over(db, owner_employee_id)
    else:
        _validate_weights_not_over(db, department_id)
    audit_service.log_from_auth(
        db,
        auth,
        action="kpi_definition.created",
        entity_type="kpi_definition",
        entity_id=row.id,
        after_state={
            "name": row.name,
            "weight": row.weight,
            "department_id": row.department_id,
            "owner_employee_id": owner_employee_id,
        },
    )
    return row


def update_definition(
    db: Session, auth: AuthContext, definition_id: int, payload: KpiDefinitionUpdate
) -> KpiDefinition:
    row = db.query(KpiDefinition).filter(KpiDefinition.id == definition_id).one_or_none()
    if row is None:
        raise EntityNotFound(f"KPI definition {definition_id} not found")
    if is_self_service(auth):
        if row.owner_employee_id != auth.linked_employee_id:
            raise PermissionDenied("You can only edit your own KPIs")
    elif row.owner_employee_id is not None:
        raise PermissionDenied("Personal KPIs can only be edited by their owner")
    before = {"name": row.name, "weight": row.weight, "target_value": str(row.target_value)}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    db.flush()
    if row.owner_employee_id is not None:
        _validate_personal_weights_not_over(db, row.owner_employee_id)
    else:
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
    if is_self_service(auth):
        if row.owner_employee_id != auth.linked_employee_id:
            raise PermissionDenied("You can only archive your own KPIs")
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
    if is_self_service(auth):
        raise PermissionDenied("Department default KPIs are managed by HR")
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
    """Format free-text work (self-service) or map to KPI catalog (HR)."""
    if is_self_service(auth):
        return _ai_format_work_submission(db, auth, payload)

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


def _ai_format_work_submission(
    db: Session, auth: AuthContext, payload: KpiAiSuggestRequest
) -> KpiAiSuggestResponse:
    """Self-service: rewrite work text professionally; suggest points to add (0–10 scale)."""
    emp_id = auth.linked_employee_id
    if emp_id is None:
        raise ValidationFailed("Your account is not linked to an employee record")
    payload = payload.model_copy(update={"employee_id": emp_id})
    emp = db.query(Employee).filter(Employee.id == emp_id).one_or_none()
    if emp is None:
        raise EntityNotFound("Employee not found")
    if payload.department_id != emp.department_id:
        payload = payload.model_copy(update={"department_id": emp.department_id})

    definition = _ensure_work_log_definition(db, emp.department_id)
    existing = _work_log_entry(
        db, emp_id, definition.id, payload.period_start, payload.period_end
    )
    current = float(existing.actual_value) if existing else 0.0
    headroom = max(0.0, float(WORK_LOG_TARGET) - current)

    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    raw_text = payload.text.strip()
    if not raw_text:
        raise ValidationFailed("Describe the work done before analyzing")

    if not api_key or api_key.startswith("your_"):
        formatted = raw_text.strip()
        if not formatted.endswith("."):
            formatted += "."
        points = min(SELF_SERVICE_POINTS_PER_ENTRY, headroom) if headroom else 0.0
        return KpiAiSuggestResponse(
            formatted_work=formatted,
            points_to_add=points,
            reasoning="Gemini not configured — kept your text with light cleanup.",
        )

    import json
    import re

    import google.generativeai as genai

    prompt = f"""You help employees log work for a monthly KPI journal (0–10 rating scale, max 10).

Employee's raw notes:
---
{raw_text}
---

Period: {payload.period_start} to {payload.period_end}
Current period score: {current:.1f} / 10 (room to add up to {headroom:.1f} more points)

Respond with STRICT JSON only:
{{"formatted_work": "<clear professional bullet or paragraph summarizing accomplishments>", "points_to_add": <number 0.5–2.0>, "reasoning": "<short>"}}

Rules:
- formatted_work: concise, professional, past tense, suitable for HR review. No markdown.
- points_to_add: default 1.0 for typical work; use 0.5 for minor tasks, up to 2.0 for major deliverables. Must not exceed {headroom:.1f}.
- If headroom is 0, set points_to_add to 0 and explain in reasoning.
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
        raise ValidationFailed(f"AI format failed: {exc}") from exc

    formatted = str(data.get("formatted_work") or raw_text).strip()
    points = float(data.get("points_to_add") or SELF_SERVICE_POINTS_PER_ENTRY)
    points = max(0.0, min(points, headroom))
    return KpiAiSuggestResponse(
        kpi_definition_id=definition.id,
        formatted_work=formatted,
        points_to_add=points,
        reasoning=str(data.get("reasoning") or "Work formatted for HR review"),
    )


def _work_log_entry(
    db: Session,
    employee_id: int,
    definition_id: int,
    period_start: date,
    period_end: date,
) -> KpiEntry | None:
    return (
        db.query(KpiEntry)
        .filter(
            KpiEntry.kpi_definition_id == definition_id,
            KpiEntry.employee_id == employee_id,
            KpiEntry.period_start == period_start,
            KpiEntry.period_end == period_end,
        )
        .one_or_none()
    )


def _split_work_items(notes: str | None) -> list[EmployeeWorkItem]:
    if not notes:
        return []
    return [
        EmployeeWorkItem(text=chunk.strip())
        for chunk in notes.split(WORK_ENTRY_SEPARATOR)
        if chunk.strip()
    ]


def _department_employee_summary(
    db: Session,
    employee_id: int,
    department_id: int,
    period_start: date,
    period_end: date,
) -> DepartmentEmployeeKpiSummary:
    definition = _ensure_work_log_definition(db, department_id)
    entry = _work_log_entry(db, employee_id, definition.id, period_start, period_end)
    contribution = round(float(entry.actual_value), 2) if entry else 0.0
    work_items = _split_work_items(entry.notes if entry else None)
    return DepartmentEmployeeKpiSummary(
        employee_id=employee_id,
        submission_count=len(work_items),
        contribution_score=contribution,
        band=work_log_band(contribution),
        work_items=work_items,
    )


def create_work_submission(
    db: Session, auth: AuthContext, payload: KpiWorkSubmissionCreate
) -> KpiEntry:
    """Self-service: append formatted work and increment period score (max 10)."""
    if not is_self_service(auth):
        raise PermissionDenied("Work submissions are for employee self-service only")
    emp_id = auth.linked_employee_id
    if emp_id is None:
        raise ValidationFailed("Your account is not linked to an employee record")

    emp = db.query(Employee).filter(Employee.id == emp_id).one_or_none()
    if emp is None:
        raise EntityNotFound("Employee not found")
    if payload.period_end < payload.period_start:
        raise ValidationFailed("period_end must be on or after period_start")

    work_text = (payload.formatted_work or payload.work_text).strip()
    if not work_text:
        raise ValidationFailed("Work description is required")

    definition = _ensure_work_log_definition(db, emp.department_id)
    existing = _work_log_entry(
        db, emp_id, definition.id, payload.period_start, payload.period_end
    )
    points = (
        float(payload.points_to_add)
        if payload.points_to_add is not None
        else SELF_SERVICE_POINTS_PER_ENTRY
    )
    points = max(0.0, min(points, float(WORK_LOG_TARGET)))

    if existing is not None:
        before = {"actual_value": str(existing.actual_value), "notes": existing.notes}
        new_actual = min(float(existing.actual_value) + points, float(WORK_LOG_TARGET))
        notes = (
            f"{existing.notes}{WORK_ENTRY_SEPARATOR}{work_text}"
            if existing.notes
            else work_text
        )
        existing.actual_value = Decimal(str(round(new_actual, 2)))
        existing.score = round(new_actual, 2)
        existing.notes = notes
        db.flush()
        audit_service.log_from_auth(
            db,
            auth,
            action="kpi_entry.corrected",
            entity_type="kpi_entry",
            entity_id=existing.id,
            before_state=before,
            after_state={
                "actual_value": str(existing.actual_value),
                "score": existing.score,
            },
        )
        return existing

    new_actual = min(points, float(WORK_LOG_TARGET))
    row = KpiEntry(
        kpi_definition_id=definition.id,
        employee_id=emp_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        actual_value=Decimal(str(round(new_actual, 2))),
        score=round(new_actual, 2),
        recorded_by=auth.user_id,
        notes=work_text,
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
            "work_submission": True,
        },
    )
    return row


# --- Entries ---


def list_entries(
    db: Session,
    auth: AuthContext,
    *,
    page: int = 1,
    page_size: int = 50,
    employee_id: int | None = None,
    department_id: int | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> PaginatedResponse[KpiEntryRead]:
    q = db.query(KpiEntry).join(KpiDefinition, KpiDefinition.id == KpiEntry.kpi_definition_id)
    own = own_employee_id(auth)
    if own is not None:
        employee_id = own
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
    if is_self_service(auth):
        if payload.employee_id != auth.linked_employee_id:
            raise PermissionDenied("You can only record KPI actuals for yourself")
        if definition.owner_employee_id not in (None, auth.linked_employee_id):
            raise PermissionDenied("You can only record against your own or department KPIs")
    if emp.department_id != definition.department_id:
        raise ValidationFailed("Employee must belong to the KPI's department")
    if definition.owner_employee_id is None and not _is_work_log_definition(definition):
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
    if is_self_service(auth) and row.employee_id != auth.linked_employee_id:
        raise PermissionDenied("You can only correct your own KPI entries")
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


def _eligible_department_employees(
    db: Session, department_id: int, period_start: date, period_end: date
) -> list[Employee]:
    employees = (
        db.query(Employee)
        .filter(Employee.department_id == department_id, Employee.status == "active")
        .all()
    )
    return [e for e in employees if _employee_in_period(e, period_start, period_end)]


def _department_summary_internal(
    db: Session, department_id: int, period_start: date, period_end: date
) -> DepartmentKpiSummary:
    if db.query(Department).filter(Department.id == department_id).one_or_none() is None:
        raise EntityNotFound(f"Department {department_id} not found")

    eligible = _eligible_department_employees(db, department_id, period_start, period_end)
    employee_summaries = [
        _department_employee_summary(db, e.id, department_id, period_start, period_end)
        for e in eligible
    ]
    submitted = [s for s in employee_summaries if s.submission_count > 0]
    entries_expected = len(eligible)
    entries_recorded = len(submitted)
    overall = (
        round(sum(s.contribution_score for s in submitted) / len(submitted), 2)
        if submitted
        else 0.0
    )
    completeness = (entries_recorded / entries_expected) if entries_expected else 1.0
    band = "complete" if eligible and all(s.contribution_score >= 10.0 for s in employee_summaries) else work_log_band(overall)
    return DepartmentKpiSummary(
        department_id=department_id,
        period_start=period_start,
        period_end=period_end,
        overall_score=overall,
        band=band,
        entries_recorded=entries_recorded,
        entries_expected=entries_expected,
        completeness=round(completeness, 4),
        employees=employee_summaries,
    )


def global_kpi_summary(
    db: Session,
    period_start: date,
    period_end: date,
    *,
    auth: AuthContext | None = None,
) -> GlobalKpiSummary:
    _ = auth
    dept_ids = [
        row.id
        for row in db.query(Department).order_by(Department.name.asc(), Department.id.asc()).all()
    ]

    departments: list[GlobalDepartmentKpiSummary] = []
    total_expected = 0
    total_recorded = 0
    scores: list[float] = []

    for department_id in dept_ids:
        dept = db.query(Department).filter(Department.id == department_id).one()
        summary = _department_summary_internal(db, department_id, period_start, period_end)
        departments.append(
            GlobalDepartmentKpiSummary(
                department_id=dept.id,
                department_name=dept.name,
                overall_score=summary.overall_score,
                band=summary.band,
                entries_recorded=summary.entries_recorded,
                entries_expected=summary.entries_expected,
                completeness=summary.completeness,
            )
        )
        total_expected += summary.entries_expected
        total_recorded += summary.entries_recorded
        if summary.entries_expected > 0:
            scores.append(summary.overall_score)

    departments.sort(key=lambda item: (-item.overall_score, item.department_name.lower()))
    overall = round(sum(scores) / len(scores), 2) if scores else 0.0
    completeness = (total_recorded / total_expected) if total_expected else 1.0
    return GlobalKpiSummary(
        period_start=period_start,
        period_end=period_end,
        overall_score=overall,
        band="complete" if departments and all(d.band == "complete" for d in departments) else work_log_band(overall),
        departments_complete=sum(1 for d in departments if d.band == "complete"),
        departments_expected=len(departments),
        entries_recorded=total_recorded,
        entries_expected=total_expected,
        completeness=round(completeness, 4),
        departments=departments,
    )


def employee_kpi_summary(
    db: Session,
    employee_id: int,
    period_start: date,
    period_end: date,
    *,
    auth: AuthContext | None = None,
) -> EmployeeKpiSummary:
    if auth is not None and is_self_service(auth) and employee_id != auth.linked_employee_id:
        raise PermissionDenied("You can only view your own KPI summary")
    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")

    contribution = _department_employee_summary(
        db, employee_id, emp.department_id, period_start, period_end
    )
    department = _department_summary_internal(db, emp.department_id, period_start, period_end)
    global_summary = global_kpi_summary(db, period_start, period_end, auth=auth)
    return EmployeeKpiSummary(
        employee_id=employee_id,
        department_id=emp.department_id,
        period_start=period_start,
        period_end=period_end,
        submission_count=contribution.submission_count,
        contribution_score=contribution.contribution_score,
        department_score=department.overall_score,
        department_band=department.band,
        global_score=global_summary.overall_score,
        global_band=global_summary.band,
        work_items=contribution.work_items,
    )


def department_kpi_summary(
    db: Session,
    department_id: int,
    period_start: date,
    period_end: date,
    *,
    auth: AuthContext | None = None,
) -> DepartmentKpiSummary:
    if auth is not None and is_self_service(auth):
        emp = db.query(Employee).filter(Employee.id == auth.linked_employee_id).one_or_none()
        if emp is None or emp.department_id != department_id:
            raise PermissionDenied("You can only view your own department KPI summary")
    return _department_summary_internal(db, department_id, period_start, period_end)


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
