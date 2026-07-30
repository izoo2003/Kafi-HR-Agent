"""PUBLIC seam — only module orchestrator/sibling agents may import.

Implements INTEGRATION_CONTRACT.md. Internally calls services the same way routes do.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.db import get_session_factory
from app.core.exceptions import NotOwnedByThisAgent
from app.integration.event_bus_stub import publish_event
from app.models.employees import Employee
from app.schemas.common import AuthContext, PERMISSION_RANK

AGENT_KEY = "hr_admin"
AGENT_VERSION = "0.1.0"

_subscribers: list[Callable[[str, dict[str, Any]], None]] = []


class AgentCapabilities(BaseModel):
    agent_key: str = AGENT_KEY
    version: str = AGENT_VERSION
    modules: list[str] = Field(
        default_factory=lambda: [
            "job_descriptions",
            "cv_screening",
            "attendance",
            "payroll",
            "kpi",
            "admin_panel",
        ]
    )
    events_emitted: list[str] = Field(
        default_factory=lambda: [
            "hr_admin.employee.created",
            "hr_admin.employee.exited",
            "hr_admin.payroll.run_approved",
            "hr_admin.candidate.hired",
            "hr_admin.kpi.period_closed",
        ]
    )
    events_consumed: list[str] = Field(
        default_factory=lambda: [
            "orchestrator.user.role_changed",
            "utilities.asset.assigned_to_employee",
        ]
    )


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded", "down"]
    db_connected: bool
    details: str | None = None


class EmployeeSummary(BaseModel):
    employee_id: int
    full_name: str
    department: str
    status: Literal["active", "on_leave", "terminated"]


class AuditEvent(BaseModel):
    agent_key: str = AGENT_KEY
    action: str
    entity_type: str
    entity_id: int
    user_id: int
    timestamp: datetime


class SiblingAgentRequest(BaseModel):
    target_agent_key: str
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SiblingAgentResponse(BaseModel):
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class RegistrationResult(BaseModel):
    status: Literal["standalone", "registered", "failed"]
    agent_key: str = AGENT_KEY
    message: str | None = None


def get_capabilities() -> AgentCapabilities:
    return AgentCapabilities()


def health_check() -> HealthStatus:
    try:
        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return HealthStatus(status="ok", db_connected=True)
    except Exception as exc:  # noqa: BLE001 — surface as degraded/down
        return HealthStatus(status="down", db_connected=False, details=str(exc))


def get_employee_summary(employee_id: int, auth: AuthContext) -> EmployeeSummary | None:
    _ = auth  # permission checks belong at caller / future orchestrator gate
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
        if emp is None:
            return None
        dept_name = emp.department.name if emp.department else ""
        status = emp.status if emp.status in ("active", "on_leave", "terminated") else "active"
        return EmployeeSummary(
            employee_id=emp.id,
            full_name=emp.full_name,
            department=dept_name,
            status=status,  # type: ignore[arg-type]
        )


def check_permission(auth: AuthContext, module_key: str, action: str) -> bool:
    key = f"{AGENT_KEY}.{module_key}"
    level = auth.agent_permissions.get(key, "none")
    return PERMISSION_RANK.get(level, 0) >= PERMISSION_RANK.get(action, 99)


def emit_audit_event(event: AuditEvent) -> None:
    """Today: publish to local stub. DB row is written by audit_service before this."""
    publish_event(
        "hr_admin.audit",
        event.model_dump(mode="json"),
    )
    for sub in _subscribers:
        sub("hr_admin.audit", event.model_dump(mode="json"))


def route_to_sibling_agent(request: SiblingAgentRequest) -> SiblingAgentResponse:
    raise NotOwnedByThisAgent(
        f"Cannot route '{request.action}' — sibling agents not wired yet.",
        expected_agent_key=request.target_agent_key or "utilities_maintenance",
    )


def register_with_orchestrator(orchestrator_url: str | None = None) -> RegistrationResult:
    _ = orchestrator_url
    return RegistrationResult(
        status="standalone",
        message="No orchestrator configured — agent running standalone.",
    )


def subscribe(handler: Callable[[str, dict[str, Any]], None]) -> None:
    """Local subscribe hook for tests / future bus adapters."""
    _subscribers.append(handler)
