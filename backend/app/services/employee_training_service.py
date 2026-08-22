"""Employee Development — AI training recommendations & assignments."""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleViolation, EntityNotFound, PermissionDenied
from app.core.gemini_client import generate_content_with_fallback
from app.core.self_service import is_self_service, own_employee_id
from app.models.employees import Employee
from app.models.kpi import EmployeeTrainingAssignment
from app.schemas.common import PERMISSION_RANK, AuthContext
from app.schemas.employee_training import (
    EmployeeTrainingAssignResponse,
    EmployeeTrainingAssignmentRead,
    EmployeeTrainingListResponse,
    EmployeeTrainingRecommendResponse,
    TrainingCourseRecommendation,
    TrainingStatus,
)
from app.services import audit_service

logger = logging.getLogger(__name__)

VALID_STATUSES = {"assigned", "in_progress", "completed"}
VALID_LEVELS = {"intermediate", "advanced"}


def _has_kpi_write(auth: AuthContext) -> bool:
    level = auth.agent_permissions.get("hr_admin.kpi", "none")
    return PERMISSION_RANK.get(level, 0) >= PERMISSION_RANK["write"]


def _resolve_employee_id(auth: AuthContext, employee_id: int | None) -> int | None:
    """Self-service must only see own; HR may pass any or None (all)."""
    if is_self_service(auth):
        own = own_employee_id(auth)
        if own is None:
            raise PermissionDenied("No linked employee record")
        if employee_id is not None and employee_id != own:
            raise PermissionDenied("You can only view your own training")
        return own
    return employee_id


def _load_employee(db: Session, employee_id: int) -> Employee:
    emp = (
        db.query(Employee)
        .options(joinedload(Employee.department))
        .filter(Employee.id == employee_id)
        .one_or_none()
    )
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")
    return emp


def _department_name(emp: Employee) -> str | None:
    if emp.department is not None:
        return emp.department.name
    return None


def _to_read(
    row: EmployeeTrainingAssignment,
    *,
    employee_name: str | None = None,
    employee_code: str | None = None,
) -> EmployeeTrainingAssignmentRead:
    return EmployeeTrainingAssignmentRead(
        id=row.id,
        employee_id=row.employee_id,
        employee_name=employee_name,
        employee_code=employee_code,
        title=row.title,
        level=row.level,  # type: ignore[arg-type]
        description=row.description,
        provider=row.provider,
        url_hint=row.url_hint,
        topic_prompt=row.topic_prompt,
        department_name=row.department_name,
        role_title=row.role_title,
        status=row.status,  # type: ignore[arg-type]
        assigned_by=row.assigned_by,
        assigned_at=row.assigned_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _parse_courses_json(raw: str) -> list[TrainingCourseRecommendation]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            raise BusinessRuleViolation("AI returned invalid course recommendations")
        data = json.loads(match.group(0))

    if isinstance(data, dict) and "courses" in data:
        data = data["courses"]
    if not isinstance(data, list):
        raise BusinessRuleViolation("AI returned invalid course recommendations")

    courses: list[TrainingCourseRecommendation] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        level_raw = str(item.get("level") or "intermediate").strip().lower()
        if "advanced" in level_raw:
            level_raw = "advanced"
        else:
            level_raw = "intermediate"
        if not title or not description:
            continue
        provider = item.get("provider")
        url_hint = item.get("url_hint") or item.get("url")
        courses.append(
            TrainingCourseRecommendation(
                title=title[:300],
                level=level_raw,  # type: ignore[arg-type]
                description=description[:2000],
                provider=(str(provider).strip()[:120] if provider else None) or None,
                url_hint=(str(url_hint).strip()[:1000] if url_hint else None) or None,
            )
        )
    if not courses:
        raise BusinessRuleViolation("AI returned no usable course recommendations")
    return courses[:5]


def recommend_courses(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int,
    topic: str,
    settings: Settings | None = None,
) -> EmployeeTrainingRecommendResponse:
    if not _has_kpi_write(auth):
        raise PermissionDenied("You need write access to recommend training")
    topic = topic.strip()
    if len(topic) < 3:
        raise BusinessRuleViolation("Please describe the training topic in a few words")

    emp = _load_employee(db, employee_id)
    dept = _department_name(emp)
    settings = settings or get_settings()
    api_keys = settings.resolved_gemini_training_api_keys()
    if not api_keys:
        raise BusinessRuleViolation(
            "Training AI is not configured. Set GEMINI_TRAINING_API_KEY "
            "(or GEMINI_API_KEY as fallback)."
        )

    prompt = f"""You are an L&D advisor for Kafi Commodities (commodities / trading / operations company).
Recommend 3 to 5 intermediate or advanced courses for this employee based on their role and the requested training topic.
Do NOT recommend beginner courses. Prefer practical, job-relevant skills.

Employee: {emp.full_name}
Department: {dept or "n/a"}
Role / position: {emp.role_title}
Training topic requested: {topic}

Return ONLY valid JSON (no markdown fences) as an array of objects with keys:
- title (string)
- level ("intermediate" or "advanced")
- description (1-3 sentences)
- provider (string, e.g. Coursera, Udemy, LinkedIn Learning, YouTube, edX)
- url_hint (optional string — search phrase or public course URL if well-known)

Example shape:
[{{"title":"...","level":"intermediate","description":"...","provider":"Coursera","url_hint":"..."}}]
"""

    try:
        response = generate_content_with_fallback(
            prompt=prompt,
            api_keys=api_keys,
            models=settings.resolved_gemini_training_models(),
            pool_id="employee_training",
        )
        text = (getattr(response, "text", None) or "").strip()
    except Exception as exc:
        logger.exception("Training recommend failed")
        raise BusinessRuleViolation(f"Could not generate course recommendations: {exc}") from exc

    courses = _parse_courses_json(text)
    return EmployeeTrainingRecommendResponse(
        employee_id=emp.id,
        employee_name=emp.full_name,
        department_name=dept,
        role_title=emp.role_title,
        topic=topic,
        courses=courses,
    )


def assign_courses(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int,
    topic: str,
    courses: list[TrainingCourseRecommendation],
) -> EmployeeTrainingAssignResponse:
    if not _has_kpi_write(auth):
        raise PermissionDenied("You need write access to assign training")
    if not courses:
        raise BusinessRuleViolation("Select at least one course to assign")
    topic = topic.strip()
    emp = _load_employee(db, employee_id)
    dept = _department_name(emp)
    now = datetime.now(UTC)
    created: list[EmployeeTrainingAssignment] = []

    for course in courses:
        level = course.level if course.level in VALID_LEVELS else "intermediate"
        row = EmployeeTrainingAssignment(
            employee_id=emp.id,
            title=course.title.strip()[:300],
            level=level,
            description=course.description.strip()[:2000],
            provider=(course.provider or None),
            url_hint=(course.url_hint or None),
            topic_prompt=topic,
            department_name=dept,
            role_title=emp.role_title,
            status="assigned",
            assigned_by=auth.user_id,
            assigned_at=now,
        )
        db.add(row)
        created.append(row)

    db.flush()
    for row in created:
        audit_service.log_from_auth(
            db,
            auth,
            action="employee_training.assigned",
            entity_type="employee_training_assignment",
            entity_id=row.id,
            after_state={
                "employee_id": emp.id,
                "title": row.title,
                "level": row.level,
                "topic": topic,
            },
        )
    db.commit()
    for row in created:
        db.refresh(row)

    return EmployeeTrainingAssignResponse(
        items=[
            _to_read(r, employee_name=emp.full_name, employee_code=emp.employee_code)
            for r in created
        ]
    )


def list_assignments(
    db: Session,
    auth: AuthContext,
    *,
    employee_id: int | None = None,
) -> EmployeeTrainingListResponse:
    resolved = _resolve_employee_id(auth, employee_id)
    q = (
        db.query(EmployeeTrainingAssignment, Employee)
        .join(Employee, Employee.id == EmployeeTrainingAssignment.employee_id)
        .order_by(
            EmployeeTrainingAssignment.assigned_at.desc(),
            EmployeeTrainingAssignment.id.desc(),
        )
    )
    if resolved is not None:
        q = q.filter(EmployeeTrainingAssignment.employee_id == resolved)
    rows = q.all()
    items = [
        _to_read(a, employee_name=e.full_name, employee_code=e.employee_code)
        for a, e in rows
    ]
    return EmployeeTrainingListResponse(items=items, total=len(items))


def update_assignment_status(
    db: Session,
    auth: AuthContext,
    *,
    assignment_id: int,
    status: TrainingStatus,
) -> EmployeeTrainingAssignmentRead:
    if status not in VALID_STATUSES:
        raise BusinessRuleViolation(f"Invalid status: {status}")

    row = (
        db.query(EmployeeTrainingAssignment)
        .filter(EmployeeTrainingAssignment.id == assignment_id)
        .one_or_none()
    )
    if row is None:
        raise EntityNotFound(f"Training assignment {assignment_id} not found")

    own = own_employee_id(auth)
    if own is None or row.employee_id != own:
        raise PermissionDenied(
            "Only the assigned employee can update training progress on Things To Learn"
        )

    before = {"status": row.status}
    row.status = status
    if status == "completed":
        row.completed_at = datetime.now(UTC)
    else:
        row.completed_at = None

    emp = db.query(Employee).filter(Employee.id == row.employee_id).one_or_none()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee_training.status_updated",
        entity_type="employee_training_assignment",
        entity_id=row.id,
        before_state=before,
        after_state={"status": status},
    )
    db.commit()
    db.refresh(row)
    return _to_read(
        row,
        employee_name=emp.full_name if emp else None,
        employee_code=emp.employee_code if emp else None,
    )
