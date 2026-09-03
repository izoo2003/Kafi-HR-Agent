"""Department CRUD service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    EntityNotFound,
    PermissionDenied,
    ValidationFailed,
)
from app.ingestion.employee_docs import delete_stored_file, read_stored_file, store_department_file
from app.models.attendance import AttendanceRule
from app.models.cv_screening import JobDescription
from app.models.employees import Department, DepartmentDocument, Employee
from app.models.kpi import KpiDefinition, KpiEntry
from app.schemas.common import PERMISSION_RANK, AuthContext
from app.schemas.employees import (
    DEPARTMENT_DOCUMENT_KINDS,
    DepartmentAiDraftRequest,
    DepartmentAiDraftResult,
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
)
from app.scoring.department_copy_generator import generate_department_copy
from app.services import audit_service

MAX_DEPARTMENT_FILES_PER_KIND = 8


def list_departments(db: Session) -> list[Department]:
    return db.query(Department).order_by(Department.name).all()


def can_read_all_department_copy(auth: AuthContext) -> bool:
    level = auth.agent_permissions.get("hr_admin.employees", "none")
    return PERMISSION_RANK.get(level, 0) >= PERMISSION_RANK["read"]


def can_view_department_copy(auth: AuthContext, department_id: int) -> bool:
    if can_read_all_department_copy(auth):
        return True
    return auth.department_id is not None and auth.department_id == department_id


def serialize_department(dept: Department, *, include_copy: bool) -> DepartmentRead:
    read = DepartmentRead.model_validate(dept)
    if include_copy:
        return read
    return read.model_copy(
        update={"job_description_text": None, "sops_text": None, "documents": []}
    )


def list_departments_for_auth(db: Session, auth: AuthContext) -> list[DepartmentRead]:
    """HR sees full JD/SOP copy; other users only see copy for their own department."""
    include_all = can_read_all_department_copy(auth)
    return [
        serialize_department(d, include_copy=include_all or auth.department_id == d.id)
        for d in list_departments(db)
    ]


def get_my_department(db: Session, auth: AuthContext) -> Department:
    if auth.department_id is None:
        raise EntityNotFound(
            "Your account is not linked to a department. Ask HR to assign you a role."
        )
    return get_department(db, auth.department_id)


def assert_can_view_department_copy(auth: AuthContext, department_id: int) -> None:
    if not can_view_department_copy(auth, department_id):
        raise PermissionDenied("You can only view documents for your own department")


def get_department(db: Session, department_id: int) -> Department:
    dept = db.query(Department).filter(Department.id == department_id).one_or_none()
    if dept is None:
        raise EntityNotFound(f"Department {department_id} not found")
    return dept


def create_department(db: Session, auth: AuthContext, payload: DepartmentCreate) -> Department:
    existing = db.query(Department).filter(Department.name == payload.name).one_or_none()
    if existing:
        raise ConflictError(f"Department '{payload.name}' already exists")
    dept = Department(
        name=payload.name,
        head_employee_id=payload.head_employee_id,
        job_description_text=payload.job_description_text,
        sops_text=payload.sops_text,
    )
    db.add(dept)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.created",
        entity_type="department",
        entity_id=dept.id,
        after_state={
            "name": dept.name,
            "job_description_text": dept.job_description_text,
            "sops_text": dept.sops_text,
        },
    )
    return dept


def update_department(
    db: Session, auth: AuthContext, department_id: int, payload: DepartmentUpdate
) -> Department:
    dept = get_department(db, department_id)
    before = {
        "name": dept.name,
        "head_employee_id": dept.head_employee_id,
        "job_description_text": dept.job_description_text,
        "sops_text": dept.sops_text,
    }
    data = payload.model_dump(exclude_unset=True)
    new_name = data.get("name")
    if new_name is not None:
        clash = (
            db.query(Department)
            .filter(Department.name == new_name, Department.id != department_id)
            .one_or_none()
        )
        if clash:
            raise ConflictError(f"Department '{new_name}' already exists")
    old_name = dept.name
    for k, v in data.items():
        setattr(dept, k, v)
    if new_name and new_name != old_name:
        db.query(Employee).filter(Employee.department_id == dept.id).update(
            {Employee.role_title: new_name},
            synchronize_session=False,
        )
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.updated",
        entity_type="department",
        entity_id=dept.id,
        before_state=before,
        after_state=data,
    )
    return dept


def delete_department(db: Session, auth: AuthContext, department_id: int) -> None:
    dept = get_department(db, department_id)
    employee_count = db.query(Employee).filter(Employee.department_id == department_id).count()
    jd_count = db.query(JobDescription).filter(JobDescription.department_id == department_id).count()
    rule_count = (
        db.query(AttendanceRule)
        .filter(AttendanceRule.applies_to_department_id == department_id)
        .count()
    )
    blockers: list[str] = []
    if employee_count:
        blockers.append(f"{employee_count} employee(s)")
    if jd_count:
        blockers.append(f"{jd_count} job description(s)")
    if rule_count:
        blockers.append(f"{rule_count} attendance rule(s)")
    if blockers:
        raise BusinessRuleViolation(
            f"Cannot remove department '{dept.name}' while it is still used by "
            + ", ".join(blockers)
            + ". Reassign or remove those records first."
        )

    # KPIs are department-scoped. A leftover / seeded definition must not block deleting
    # a unused department — remove entries then definitions for this department.
    kpi_ids = [
        row.id
        for row in db.query(KpiDefinition.id).filter(KpiDefinition.department_id == department_id).all()
    ]
    kpi_removed = len(kpi_ids)
    if kpi_ids:
        db.query(KpiEntry).filter(KpiEntry.kpi_definition_id.in_(kpi_ids)).delete(
            synchronize_session=False
        )
        db.query(KpiDefinition).filter(KpiDefinition.id.in_(kpi_ids)).delete(
            synchronize_session=False
        )

    name = dept.name
    for doc in list(dept.documents or []):
        delete_stored_file(doc.file_path)
    db.delete(dept)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.deleted",
        entity_type="department",
        entity_id=department_id,
        before_state={"name": name, "kpi_definitions_removed": kpi_removed},
    )


def generate_ai_draft(payload: DepartmentAiDraftRequest) -> DepartmentAiDraftResult:
    text = generate_department_copy(
        name=payload.name,
        kind=payload.kind,
        settings=get_settings(),
    )
    return DepartmentAiDraftResult(kind=payload.kind, text=text)


def add_department_documents(
    db: Session,
    auth: AuthContext,
    department_id: int,
    *,
    kind: str,
    files: list[tuple[str, bytes]],
) -> list[DepartmentDocument]:
    dept = get_department(db, department_id)
    kind_key = (kind or "").strip().lower()
    if kind_key not in DEPARTMENT_DOCUMENT_KINDS:
        raise ValidationFailed("kind must be job_description or sop")
    if not files:
        raise ValidationFailed("At least one file is required")
    existing = sum(1 for d in (dept.documents or []) if d.kind == kind_key)
    if existing + len(files) > MAX_DEPARTMENT_FILES_PER_KIND:
        raise ValidationFailed(
            f"At most {MAX_DEPARTMENT_FILES_PER_KIND} attachments per Job Description or SOP"
        )
    created: list[DepartmentDocument] = []
    for filename, content in files:
        path, mime = store_department_file(
            department_id=dept.id,
            kind=kind_key,
            filename=filename,
            content=content,
        )
        doc = DepartmentDocument(
            department_id=dept.id,
            kind=kind_key,
            file_path=path,
            original_filename=filename,
            mime_type=mime,
        )
        db.add(doc)
        created.append(doc)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="department.documents_uploaded",
        entity_type="department",
        entity_id=dept.id,
        after_state={
            "kind": kind_key,
            "count": len(created),
            "filenames": [d.original_filename for d in created],
        },
    )
    return created


def get_department_document(
    db: Session, department_id: int, document_id: int
) -> DepartmentDocument:
    doc = (
        db.query(DepartmentDocument)
        .filter(
            DepartmentDocument.id == document_id,
            DepartmentDocument.department_id == department_id,
        )
        .one_or_none()
    )
    if doc is None:
        raise EntityNotFound(f"Document {document_id} not found for department {department_id}")
    return doc


def read_document_bytes(file_path: str) -> bytes:
    return read_stored_file(file_path)


def delete_department_document(
    db: Session, auth: AuthContext, department_id: int, document_id: int
) -> None:
    doc = get_department_document(db, department_id, document_id)
    path = doc.file_path
    before = {"filename": doc.original_filename, "kind": doc.kind}
    db.delete(doc)
    db.flush()
    delete_stored_file(path)
    audit_service.log_from_auth(
        db,
        auth,
        action="department.document_deleted",
        entity_type="department_document",
        entity_id=document_id,
        before_state=before,
    )
