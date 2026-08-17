"""Employee CRUD service + documents / references."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, EntityNotFound, ValidationFailed
from app.ingestion.employee_docs import delete_stored_file, read_stored_file, store_employee_file
from app.models.employees import (
    Department,
    Employee,
    EmployeeDocument,
    EmployeeReference,
    EmployeeReferenceDocument,
)
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.employees import (
    DOCUMENT_CATEGORIES,
    IMAGE_ONLY_DOCUMENT_CATEGORIES,
    EmployeeCreate,
    EmployeeDetailRead,
    EmployeeDocumentRead,
    EmployeeRead,
    EmployeeReferenceCreate,
    EmployeeReferenceDocumentRead,
    EmployeeReferenceRead,
    EmployeeReferenceUpdate,
    EmployeeUpdate,
)
from app.services import audit_service


def list_employees(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    department_id: int | None = None,
    status: str | None = None,
) -> PaginatedResponse[EmployeeRead]:
    q = db.query(Employee)
    if department_id is not None:
        q = q.filter(Employee.department_id == department_id)
    if status is not None:
        q = q.filter(Employee.status == status)
    total = q.count()
    rows = (
        q.order_by(Employee.full_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=[EmployeeRead.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.query(Employee).filter(Employee.id == employee_id).one_or_none()
    if emp is None:
        raise EntityNotFound(f"Employee {employee_id} not found")
    return emp


def get_employee_detail(db: Session, employee_id: int) -> EmployeeDetailRead:
    emp = get_employee(db, employee_id)
    return EmployeeDetailRead.model_validate(emp)


def _resolve_role_title(db: Session, department_id: int, role_title: str | None) -> str:
    dept = db.query(Department).filter(Department.id == department_id).one_or_none()
    if dept is None:
        raise ValidationFailed("department_id does not exist")
    title = (role_title or "").strip()
    return title or dept.name


def create_employee(db: Session, auth: AuthContext, payload: EmployeeCreate) -> Employee:
    if db.query(Employee).filter(Employee.employee_code == payload.employee_code).one_or_none():
        raise ConflictError(f"employee_code '{payload.employee_code}' already exists")
    data = payload.model_dump()
    data["role_title"] = _resolve_role_title(db, payload.department_id, payload.role_title)
    emp = Employee(**data)
    db.add(emp)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.created",
        entity_type="employee",
        entity_id=emp.id,
        after_state={"employee_code": emp.employee_code, "full_name": emp.full_name},
    )
    return emp


def update_employee(
    db: Session, auth: AuthContext, employee_id: int, payload: EmployeeUpdate
) -> Employee:
    emp = get_employee(db, employee_id)
    before = {"full_name": emp.full_name, "status": emp.status, "department_id": emp.department_id}
    data = payload.model_dump(exclude_unset=True)
    if "department_id" in data or "role_title" in data:
        dept_id = data.get("department_id", emp.department_id)
        role = data.get("role_title", emp.role_title)
        # When department changes and role_title was not explicitly set, sync to dept name.
        if "department_id" in data and "role_title" not in data:
            role = None
        data["role_title"] = _resolve_role_title(db, dept_id, role)
        if "department_id" in data:
            # _resolve_role_title already validated dept exists
            pass
    for k, v in data.items():
        setattr(emp, k, v)
    db.flush()
    after = {
        k: str(v) if isinstance(v, Decimal) else v for k, v in data.items()
    }
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.updated",
        entity_type="employee",
        entity_id=emp.id,
        before_state=before,
        after_state=after,
    )
    return emp


def exit_employee(db: Session, auth: AuthContext, employee_id: int) -> Employee:
    emp = get_employee(db, employee_id)
    before = {"status": emp.status, "date_exited": str(emp.date_exited) if emp.date_exited else None}
    emp.status = "terminated"
    emp.date_exited = date.today()
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.exited",
        entity_type="employee",
        entity_id=emp.id,
        before_state=before,
        after_state={"status": emp.status, "date_exited": str(emp.date_exited)},
    )
    return emp


# --- Documents -----------------------------------------------------------------


def add_employee_documents(
    db: Session,
    auth: AuthContext,
    employee_id: int,
    *,
    category: str,
    title: str | None,
    files: list[tuple[str, bytes]],
) -> list[EmployeeDocument]:
    emp = get_employee(db, employee_id)
    cat = (category or "").strip().lower()
    if cat not in DOCUMENT_CATEGORIES:
        raise ValidationFailed(
            f"Invalid category '{category}'. Use one of: {', '.join(sorted(DOCUMENT_CATEGORIES))}"
        )
    if not files:
        raise ValidationFailed("At least one file is required")

    images_only = cat in IMAGE_ONLY_DOCUMENT_CATEGORIES
    created: list[EmployeeDocument] = []
    for filename, content in files:
        path, mime = store_employee_file(
            employee_id=emp.id,
            filename=filename,
            content=content,
            subdir="documents",
            images_only=images_only,
        )
        doc = EmployeeDocument(
            employee_id=emp.id,
            category=cat,
            title=title,
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
        action="employee.documents_uploaded",
        entity_type="employee",
        entity_id=emp.id,
        after_state={
            "category": cat,
            "count": len(created),
            "filenames": [d.original_filename for d in created],
        },
    )
    return created


def get_employee_document(db: Session, employee_id: int, document_id: int) -> EmployeeDocument:
    doc = (
        db.query(EmployeeDocument)
        .filter(EmployeeDocument.id == document_id, EmployeeDocument.employee_id == employee_id)
        .one_or_none()
    )
    if doc is None:
        raise EntityNotFound(f"Document {document_id} not found for employee {employee_id}")
    return doc


def delete_employee_document(
    db: Session, auth: AuthContext, employee_id: int, document_id: int
) -> None:
    doc = get_employee_document(db, employee_id, document_id)
    path = doc.file_path
    before = {"filename": doc.original_filename, "category": doc.category}
    db.delete(doc)
    db.flush()
    delete_stored_file(path)
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.document_deleted",
        entity_type="employee_document",
        entity_id=document_id,
        before_state=before,
    )


# --- References ----------------------------------------------------------------


def create_reference(
    db: Session, auth: AuthContext, employee_id: int, payload: EmployeeReferenceCreate
) -> EmployeeReference:
    emp = get_employee(db, employee_id)
    ref = EmployeeReference(employee_id=emp.id, **payload.model_dump())
    db.add(ref)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.reference_created",
        entity_type="employee_reference",
        entity_id=ref.id,
        after_state={"full_name": ref.full_name, "relation": ref.relation},
    )
    return ref


def get_reference(db: Session, employee_id: int, reference_id: int) -> EmployeeReference:
    ref = (
        db.query(EmployeeReference)
        .filter(EmployeeReference.id == reference_id, EmployeeReference.employee_id == employee_id)
        .one_or_none()
    )
    if ref is None:
        raise EntityNotFound(f"Reference {reference_id} not found for employee {employee_id}")
    return ref


def update_reference(
    db: Session,
    auth: AuthContext,
    employee_id: int,
    reference_id: int,
    payload: EmployeeReferenceUpdate,
) -> EmployeeReference:
    ref = get_reference(db, employee_id, reference_id)
    before = {"full_name": ref.full_name, "relation": ref.relation}
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(ref, k, v)
    db.flush()
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.reference_updated",
        entity_type="employee_reference",
        entity_id=ref.id,
        before_state=before,
        after_state=data,
    )
    return ref


def delete_reference(
    db: Session, auth: AuthContext, employee_id: int, reference_id: int
) -> None:
    ref = get_reference(db, employee_id, reference_id)
    paths = [d.file_path for d in ref.documents]
    before = {"full_name": ref.full_name}
    db.delete(ref)
    db.flush()
    for p in paths:
        delete_stored_file(p)
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.reference_deleted",
        entity_type="employee_reference",
        entity_id=reference_id,
        before_state=before,
    )


def add_reference_documents(
    db: Session,
    auth: AuthContext,
    employee_id: int,
    reference_id: int,
    files: list[tuple[str, bytes]],
) -> list[EmployeeReferenceDocument]:
    ref = get_reference(db, employee_id, reference_id)
    if not files:
        raise ValidationFailed("At least one file is required")
    created: list[EmployeeReferenceDocument] = []
    for filename, content in files:
        path, mime = store_employee_file(
            employee_id=employee_id,
            filename=filename,
            content=content,
            subdir=f"references/{reference_id}",
        )
        doc = EmployeeReferenceDocument(
            reference_id=ref.id,
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
        action="employee.reference_documents_uploaded",
        entity_type="employee_reference",
        entity_id=ref.id,
        after_state={"count": len(created), "filenames": [d.original_filename for d in created]},
    )
    return created


def get_reference_document(
    db: Session, employee_id: int, reference_id: int, document_id: int
) -> EmployeeReferenceDocument:
    get_reference(db, employee_id, reference_id)
    doc = (
        db.query(EmployeeReferenceDocument)
        .filter(
            EmployeeReferenceDocument.id == document_id,
            EmployeeReferenceDocument.reference_id == reference_id,
        )
        .one_or_none()
    )
    if doc is None:
        raise EntityNotFound(f"Reference document {document_id} not found")
    return doc


def delete_reference_document(
    db: Session,
    auth: AuthContext,
    employee_id: int,
    reference_id: int,
    document_id: int,
) -> None:
    doc = get_reference_document(db, employee_id, reference_id, document_id)
    path = doc.file_path
    before = {"filename": doc.original_filename}
    db.delete(doc)
    db.flush()
    delete_stored_file(path)
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.reference_document_deleted",
        entity_type="employee_reference_document",
        entity_id=document_id,
        before_state=before,
    )


def resolve_file_path(file_path: str) -> Path:
    """Legacy helper — local disk only. Prefer read_document_bytes for downloads."""
    if file_path.startswith("supabase://"):
        raise EntityNotFound("File is stored in Supabase Storage — use read_document_bytes")
    path = Path(file_path)
    if not path.is_file():
        raise EntityNotFound("File not found on disk")
    return path


def read_document_bytes(file_path: str) -> bytes:
    """Load document bytes from Supabase Storage or local disk."""
    return read_stored_file(file_path)


# Re-export read helpers used by routes
__all__ = [
    "list_employees",
    "get_employee",
    "get_employee_detail",
    "create_employee",
    "update_employee",
    "exit_employee",
    "add_employee_documents",
    "get_employee_document",
    "delete_employee_document",
    "create_reference",
    "get_reference",
    "update_reference",
    "delete_reference",
    "add_reference_documents",
    "get_reference_document",
    "delete_reference_document",
    "resolve_file_path",
    "read_document_bytes",
    "EmployeeDocumentRead",
    "EmployeeReferenceRead",
    "EmployeeReferenceDocumentRead",
]
