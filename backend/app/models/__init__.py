"""Import all models so Alembic / metadata see every table."""
from app.models.attendance import AttendanceRecord, AttendanceRule, LeaveRequest
from app.models.audit import AuditLog
from app.models.cv_screening import (
    Candidate,
    CandidateRanking,
    CandidateScore,
    JobDescription,
    ScoringCriteria,
)
from app.models.employees import (
    Department,
    DepartmentDocument,
    Employee,
    EmployeeDocument,
    EmployeeReference,
    EmployeeReferenceDocument,
)
from app.models.identity import (
    AgentAccessMatrix,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.models.kpi import (
    EmployeeMonthlyPerformance,
    EmployeeResignationNotice,
    EmployeeTrainingAssignment,
    KpiDefinition,
    KpiEntry,
)
from app.models.payroll import (
    Deduction,
    PayrollRun,
    PayrollSheetAdjustment,
    PayrollStructure,
    Payslip,
    SalaryAdvance,
    TaxSlab,
    TaxYear,
)
from app.models.system import IntegrationRegistry, SystemConfig
from app.models.notification import AppNotification
from app.models.whatsapp import WhatsAppInboundMessage

__all__ = [
    "User",
    "Role",
    "UserRole",
    "AgentAccessMatrix",
    "Permission",
    "RolePermission",
    "Department",
    "DepartmentDocument",
    "Employee",
    "EmployeeDocument",
    "EmployeeReference",
    "EmployeeReferenceDocument",
    "JobDescription",
    "ScoringCriteria",
    "Candidate",
    "CandidateScore",
    "CandidateRanking",
    "AttendanceRule",
    "AttendanceRecord",
    "LeaveRequest",
    "PayrollStructure",
    "PayrollRun",
    "Payslip",
    "Deduction",
    "SalaryAdvance",
    "PayrollSheetAdjustment",
    "TaxYear",
    "TaxSlab",
    "KpiDefinition",
    "KpiEntry",
    "EmployeeMonthlyPerformance",
    "EmployeeTrainingAssignment",
    "EmployeeResignationNotice",
    "AuditLog",
    "IntegrationRegistry",
    "SystemConfig",
    "WhatsAppInboundMessage",
    "AppNotification",
]
