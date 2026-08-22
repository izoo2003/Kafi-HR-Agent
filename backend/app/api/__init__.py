"""Mount all /api/v1 routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    attendance,
    audit_log,
    auth,
    cnic,
    education_documents,
    cv_screening,
    employee_letters,
    employee_performance,
    employee_resignation,
    employee_training,
    employees,
    integration,
    job_descriptions,
    kpi,
    notifications,
    payroll,
    users,
    whatsapp_webhook,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(cnic.router)
api_router.include_router(education_documents.router)
api_router.include_router(employee_letters.router)
api_router.include_router(employees.router)
api_router.include_router(job_descriptions.router)
api_router.include_router(cv_screening.router)
api_router.include_router(attendance.router)
api_router.include_router(payroll.router)
api_router.include_router(kpi.router)
api_router.include_router(employee_performance.router)
api_router.include_router(employee_training.router)
api_router.include_router(employee_resignation.router)
api_router.include_router(notifications.router)
api_router.include_router(audit_log.router)
api_router.include_router(integration.router)
api_router.include_router(whatsapp_webhook.router)
