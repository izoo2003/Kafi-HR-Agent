"""Employee & department routes — API_ENDPOINTS.md §3."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.orm import Session
from urllib.parse import quote

from app.core.db import get_db
from app.core.deps import get_current_user, require_permission
from app.core.exceptions import ValidationFailed
from app.schemas.cnic import CnicVerificationResult
from app.schemas.common import AuthContext, PaginatedResponse
from app.schemas.employees import (
    DepartmentAiDraftRequest,
    DepartmentAiDraftResult,
    DepartmentCreate,
    DepartmentDocumentRead,
    DepartmentRead,
    DepartmentUpdate,
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
from app.services import department_service, employee_service

router = APIRouter(tags=["employees"])


@router.get("/departments", response_model=list[DepartmentRead])
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
) -> list[DepartmentRead]:
    """Department names are needed for KPI/attendance. JD/SOP copy is only included for HR, or for the caller's own department."""
    return department_service.list_departments_for_auth(db, auth)


@router.get("/departments/me", response_model=DepartmentRead)
def get_my_department(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
) -> DepartmentRead:
    """Job description and SOPs for the signed-in user's assigned department."""
    return DepartmentRead.model_validate(department_service.get_my_department(db, auth))


@router.post("/departments/ai-draft", response_model=DepartmentAiDraftResult)
def ai_draft_department(
    payload: DepartmentAiDraftRequest,
    _: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> DepartmentAiDraftResult:
    """Generate department Job Description or SOP text from the department name."""
    return department_service.generate_ai_draft(payload)


@router.post("/departments", response_model=DepartmentRead, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> DepartmentRead:
    return DepartmentRead.model_validate(department_service.create_department(db, auth, payload))


@router.patch("/departments/{department_id}", response_model=DepartmentRead)
def patch_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> DepartmentRead:
    return DepartmentRead.model_validate(
        department_service.update_department(db, auth, department_id, payload)
    )


@router.delete("/departments/{department_id}", status_code=204)
def delete_department(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> Response:
    department_service.delete_department(db, auth, department_id)
    return Response(status_code=204)


@router.post(
    "/departments/{department_id}/documents",
    response_model=list[DepartmentDocumentRead],
    status_code=201,
)
async def upload_department_documents(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
    kind: Annotated[str, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
) -> list[DepartmentDocumentRead]:
    payloads: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        name = f.filename or "upload.bin"
        if not Path(name).suffix and f.content_type:
            ctype = f.content_type.split(";", 1)[0].strip().lower()
            if ctype == "application/pdf":
                name = "upload.pdf"
            elif ctype.startswith("image/"):
                subtype = ctype.split("/", 1)[-1]
                ext = {
                    "jpeg": ".jpg",
                    "jpg": ".jpg",
                    "png": ".png",
                    "webp": ".webp",
                    "gif": ".gif",
                    "heic": ".heic",
                }.get(subtype, ".jpg")
                name = f"upload{ext}"
        payloads.append((name, content))
    if not payloads:
        raise ValidationFailed("At least one file is required")
    docs = department_service.add_department_documents(
        db, auth, department_id, kind=kind, files=payloads
    )
    return [DepartmentDocumentRead.model_validate(d) for d in docs]


@router.get("/departments/{department_id}/documents/{document_id}/file")
def download_department_document(
    department_id: int,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(get_current_user)],
) -> Response:
    department_service.assert_can_view_department_copy(auth, department_id)
    doc = department_service.get_department_document(db, department_id, document_id)
    data = department_service.read_document_bytes(doc.file_path)
    filename = doc.original_filename or "attachment"
    return Response(
        content=data,
        media_type=doc.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.delete(
    "/departments/{department_id}/documents/{document_id}",
    status_code=204,
    response_class=Response,
)
def delete_department_document(
    department_id: int,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> Response:
    department_service.delete_department_document(db, auth, department_id, document_id)
    return Response(status_code=204)


@router.get("/employees", response_model=PaginatedResponse[EmployeeRead])
def list_employees(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    department_id: int | None = None,
    status: str | None = None,
) -> PaginatedResponse[EmployeeRead]:
    return employee_service.list_employees(
        db, page=page, page_size=page_size, department_id=department_id, status=status
    )


@router.post("/employees", response_model=EmployeeRead, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeRead:
    return EmployeeRead.model_validate(employee_service.create_employee(db, auth, payload))


@router.post("/employees/cnic/verify", response_model=CnicVerificationResult, deprecated=True)
async def verify_employee_cnic_legacy(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
    typed_cnic: Annotated[str, Form(...)],
    front_image: Annotated[UploadFile | None, File()] = None,
    back_image: Annotated[UploadFile | None, File()] = None,
    image: Annotated[UploadFile | None, File()] = None,
) -> CnicVerificationResult:
    """Deprecated alias — prefer POST /cnic/verify."""
    from app.api.routes.cnic import verify_cnic_endpoint

    return await verify_cnic_endpoint(
        db=db,
        auth=auth,
        typed_cnic=typed_cnic,
        front_image=front_image,
        back_image=back_image,
        image=image,
    )


@router.get("/employees/{employee_id}", response_model=EmployeeDetailRead)
def get_employee(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
) -> EmployeeDetailRead:
    return employee_service.get_employee_detail(db, employee_id)


@router.patch("/employees/{employee_id}", response_model=EmployeeDetailRead)
def patch_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeDetailRead:
    employee_service.update_employee(db, auth, employee_id, payload)
    return employee_service.get_employee_detail(db, employee_id)


@router.delete("/employees/{employee_id}", response_model=EmployeeRead)
def delete_employee(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeRead:
    return EmployeeRead.model_validate(employee_service.exit_employee(db, auth, employee_id))


# --- Documents -----------------------------------------------------------------


@router.post(
    "/employees/{employee_id}/documents",
    response_model=list[EmployeeDocumentRead],
    status_code=201,
)
async def upload_employee_documents(
    employee_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
    category: Annotated[str, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
    title: Annotated[str | None, Form()] = None,
) -> list[EmployeeDocumentRead]:
    payloads: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        name = f.filename or "upload.bin"
        # Prefer filename extension; if missing, map from content-type for images.
        if not Path(name).suffix and f.content_type and f.content_type.startswith("image/"):
            subtype = f.content_type.split("/", 1)[-1].split(";")[0].strip().lower()
            ext = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "webp": ".webp", "gif": ".gif", "heic": ".heic"}.get(
                subtype, ".jpg"
            )
            name = f"upload{ext}"
        payloads.append((name, content))
    if not payloads:
        raise ValidationFailed("At least one file is required")
    docs = employee_service.add_employee_documents(
        db, auth, employee_id, category=category, title=title, files=payloads
    )
    return [EmployeeDocumentRead.model_validate(d) for d in docs]


@router.get("/employees/{employee_id}/documents/{document_id}/file")
def download_employee_document(
    employee_id: int,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
) -> Response:
    doc = employee_service.get_employee_document(db, employee_id, document_id)
    data = employee_service.read_document_bytes(doc.file_path)
    filename = doc.original_filename or "document"
    return Response(
        content=data,
        media_type=doc.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.delete(
    "/employees/{employee_id}/documents/{document_id}",
    status_code=204,
    response_class=Response,
)
def delete_employee_document(
    employee_id: int,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> Response:
    employee_service.delete_employee_document(db, auth, employee_id, document_id)
    return Response(status_code=204)


# --- References ----------------------------------------------------------------


@router.post(
    "/employees/{employee_id}/references",
    response_model=EmployeeReferenceRead,
    status_code=201,
)
def create_reference(
    employee_id: int,
    payload: EmployeeReferenceCreate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeReferenceRead:
    ref = employee_service.create_reference(db, auth, employee_id, payload)
    return EmployeeReferenceRead.model_validate(ref)


@router.patch(
    "/employees/{employee_id}/references/{reference_id}",
    response_model=EmployeeReferenceRead,
)
def patch_reference(
    employee_id: int,
    reference_id: int,
    payload: EmployeeReferenceUpdate,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> EmployeeReferenceRead:
    ref = employee_service.update_reference(db, auth, employee_id, reference_id, payload)
    return EmployeeReferenceRead.model_validate(ref)


@router.delete(
    "/employees/{employee_id}/references/{reference_id}",
    status_code=204,
    response_class=Response,
)
def delete_reference(
    employee_id: int,
    reference_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> Response:
    employee_service.delete_reference(db, auth, employee_id, reference_id)
    return Response(status_code=204)


@router.post(
    "/employees/{employee_id}/references/{reference_id}/documents",
    response_model=list[EmployeeReferenceDocumentRead],
    status_code=201,
)
async def upload_reference_documents(
    employee_id: int,
    reference_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
    files: Annotated[list[UploadFile], File(...)],
) -> list[EmployeeReferenceDocumentRead]:
    payloads: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        payloads.append((f.filename or "upload.bin", content))
    docs = employee_service.add_reference_documents(
        db, auth, employee_id, reference_id, payloads
    )
    return [EmployeeReferenceDocumentRead.model_validate(d) for d in docs]


@router.get(
    "/employees/{employee_id}/references/{reference_id}/documents/{document_id}/file"
)
def download_reference_document(
    employee_id: int,
    reference_id: int,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(require_permission("employees", "read"))],
) -> Response:
    doc = employee_service.get_reference_document(db, employee_id, reference_id, document_id)
    data = employee_service.read_document_bytes(doc.file_path)
    filename = doc.original_filename or "document"
    return Response(
        content=data,
        media_type=doc.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
    )


@router.delete(
    "/employees/{employee_id}/references/{reference_id}/documents/{document_id}",
    status_code=204,
    response_class=Response,
)
def delete_reference_document(
    employee_id: int,
    reference_id: int,
    document_id: int,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> Response:
    employee_service.delete_reference_document(
        db, auth, employee_id, reference_id, document_id
    )
    return Response(status_code=204)
