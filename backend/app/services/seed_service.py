"""Seed roles, access matrix, system config, and bootstrap admin user."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.identity import AgentAccessMatrix, Role, User
from app.models.system import IntegrationRegistry, SystemConfig

logger = logging.getLogger(__name__)

AGENT_KEY = "hr_admin"

MODULES = [
    "job_descriptions",
    "cv_screening",
    "attendance",
    "payroll",
    "kpi",
    "admin_panel",
    "employees",
    "users",
]

# Role → module → permission level (AUTH_AND_RBAC.md seed intent)
ROLE_MATRIX: dict[str, dict[str, str]] = {
    "super_admin": {m: "admin" for m in MODULES},
    "hr_manager": {
        "job_descriptions": "admin",
        "cv_screening": "admin",
        "attendance": "write",
        "payroll": "approve",
        "kpi": "admin",
        "admin_panel": "read",
        "employees": "admin",
        "users": "write",
    },
    "payroll_officer": {
        "job_descriptions": "none",
        "cv_screening": "none",
        "attendance": "read",
        "payroll": "admin",
        "kpi": "read",
        "admin_panel": "none",
        "employees": "read",
        "users": "none",
    },
    "department_head": {
        "job_descriptions": "read",
        "cv_screening": "read",
        "attendance": "approve",
        "payroll": "none",
        "kpi": "write",
        "admin_panel": "none",
        "employees": "read",
        "users": "none",
    },
    "recruiter": {
        "job_descriptions": "admin",
        "cv_screening": "admin",
        "attendance": "none",
        "payroll": "none",
        "kpi": "none",
        "admin_panel": "none",
        "employees": "read",
        "users": "none",
    },
    "employee": {
        "job_descriptions": "none",
        "cv_screening": "none",
        "attendance": "read",
        "payroll": "read",
        "kpi": "write",
        "admin_panel": "none",
        "employees": "none",
        "users": "none",
    },
    "readonly_auditor": {
        **{m: "read" for m in MODULES},
        "attendance": "write",
    },
}

ROLE_DESCRIPTIONS = {
    "super_admin": "Full access to everything, including admin panel and system config",
    "hr_manager": "Full access to CV screening, employees, KPI; read/approve on payroll",
    "payroll_officer": "Full access to payroll, read-only elsewhere",
    "department_head": "Department employees/KPI/attendance; approve leave for team",
    "recruiter": "Job descriptions & CV screening only",
    "employee": "Self-service: create account with username + PIN; own attendance and KPIs",
    "readonly_auditor": "Read-only across modules except attendance (can mark/import); includes audit logs",
}


def seed_roles_and_matrix(db: Session) -> None:
    for name, desc in ROLE_DESCRIPTIONS.items():
        role = db.query(Role).filter(Role.name == name).one_or_none()
        if role is None:
            role = Role(name=name, description=desc)
            db.add(role)
            db.flush()

        matrix = ROLE_MATRIX.get(name, {})
        for module_key, permission in matrix.items():
            existing = (
                db.query(AgentAccessMatrix)
                .filter_by(role_id=role.id, agent_key=AGENT_KEY, module_key=module_key)
                .one_or_none()
            )
            if existing is None:
                db.add(
                    AgentAccessMatrix(
                        role_id=role.id,
                        agent_key=AGENT_KEY,
                        module_key=module_key,
                        permission=permission,
                    )
                )
            else:
                existing.permission = permission


def seed_admin_user(db: Session) -> None:
    settings = get_settings()
    user = db.query(User).filter(User.email == settings.seed_admin_email.lower()).one_or_none()
    if user is None:
        user = User(
            email=settings.seed_admin_email.lower(),
            password_hash=hash_password(settings.seed_admin_password),
            full_name=settings.seed_admin_name,
            is_active=True,
        )
        db.add(user)
        db.flush()
        logger.info("Seeded admin user %s", settings.seed_admin_email)

    admin_role = db.query(Role).filter(Role.name == "super_admin").one()
    if admin_role not in user.roles:
        user.roles.append(admin_role)


# Demo logins for local walkthroughs (dev only). Shared password for all except seed admin.
DEMO_PASSWORD = "DemoPass123!"
DEMO_USERS: list[tuple[str, str, str]] = [
    ("hr.manager@kafi-group.com", "HR Manager", "hr_manager"),
    ("recruiter@kafi-group.com", "Recruiter", "recruiter"),
    ("dept.head@kafi-group.com", "Department Head", "department_head"),
    ("payroll@kafi-group.com", "Payroll Officer", "payroll_officer"),
    ("employee@kafi-group.com", "Sample Employee", "employee"),
    ("auditor@kafi-group.com", "Readonly Auditor", "readonly_auditor"),
]


def seed_demo_users(db: Session) -> None:
    """Idempotent demo accounts so you can log in as each role without the admin panel UI."""
    for email, full_name, role_name in DEMO_USERS:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name=full_name,
                is_active=True,
            )
            db.add(user)
            db.flush()
            logger.info("Seeded demo user %s (%s)", email, role_name)
        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if role is not None and role not in user.roles:
            user.roles.append(role)


DEFAULT_DEPARTMENTS = [
    "General",
    "Operations",
    "Accounting",
    "Sales",
    "HR",
    "Digital Marketing",
    "Graphic Design",
    "Engineering",
    "Customer Support",
    "IT",
]


def seed_default_department(db: Session) -> None:
    from app.models.employees import Department

    existing = {d.name for d in db.query(Department).all()}
    for name in DEFAULT_DEPARTMENTS:
        if name not in existing:
            db.add(Department(name=name))
    db.flush()


def seed_demo_org(db: Session) -> None:
    """Minimal org data so attendance/KPI/CV screens aren't empty on first login."""
    from datetime import date
    from decimal import Decimal

    from app.models.employees import Department, Employee

    general = db.query(Department).filter(Department.name == "General").one()
    ops = db.query(Department).filter(Department.name == "Operations").one()

    emp_user = db.query(User).filter(User.email == "employee@kafi-group.com").one_or_none()
    head_user = db.query(User).filter(User.email == "dept.head@kafi-group.com").one_or_none()

    def _ensure_employee(
        *,
        code: str,
        name: str,
        dept_id: int,
        role_title: str,
        user_id: int | None,
        base_salary: Decimal,
    ) -> Employee:
        row = db.query(Employee).filter(Employee.employee_code == code).one_or_none()
        if row is None:
            row = Employee(
                employee_code=code,
                full_name=name,
                department_id=dept_id,
                role_title=role_title,
                employment_type="full_time",
                date_joined=date(2025, 1, 15),
                status="active",
                base_salary=base_salary,
                user_id=user_id,
            )
            db.add(row)
            db.flush()
        elif user_id is not None and row.user_id is None:
            row.user_id = user_id
        return row

    _ensure_employee(
        code="E001",
        name="Sample Employee",
        dept_id=ops.id,
        role_title="Associate",
        user_id=emp_user.id if emp_user else None,
        base_salary=Decimal("75000"),
    )
    _ensure_employee(
        code="E002",
        name="Department Head",
        dept_id=ops.id,
        role_title="Operations Lead",
        user_id=head_user.id if head_user else None,
        base_salary=Decimal("120000"),
    )
    _ensure_employee(
        code="E003",
        name="Jane Analyst",
        dept_id=general.id,
        role_title="Analyst",
        user_id=None,
        base_salary=Decimal("90000"),
    )


def seed_integration_registry(db: Session) -> None:
    row = db.query(IntegrationRegistry).filter_by(agent_key=AGENT_KEY).one_or_none()
    if row is None:
        db.add(IntegrationRegistry(agent_key=AGENT_KEY, status="standalone"))


def seed_system_config_from_yaml(db: Session) -> None:
    settings = get_settings()
    config_dir: Path = settings.config_dir
    if not config_dir.exists():
        return
    for path in sorted(config_dir.glob("*.yaml")):
        key = f"file.{path.stem}"
        existing = db.query(SystemConfig).filter_by(key=key).one_or_none()
        if existing is not None:
            continue
        try:
            data: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping config seed for %s: %s", path.name, exc)
            continue
        db.add(SystemConfig(key=key, value=data, updated_by=None))


def run_all_seeds(db: Session) -> None:
    from app.services.auth_service import ensure_self_service_schema

    ensure_self_service_schema(db)
    from app.services.linkedin_service import ensure_linkedin_schema

    ensure_linkedin_schema(db)
    seed_roles_and_matrix(db)
    seed_admin_user(db)
    seed_demo_users(db)
    seed_integration_registry(db)
    seed_system_config_from_yaml(db)
    seed_default_department(db)
    seed_demo_org(db)
    from app.services.attendance_service import ensure_attendance_config, ensure_default_rule
    from app.services.kpi_service import ensure_kpi_config
    from app.services.tax_service import ensure_default_tax_year

    ensure_default_rule(db)
    ensure_attendance_config(db)
    ensure_kpi_config(db)
    ensure_default_tax_year(db)
    db.commit()
