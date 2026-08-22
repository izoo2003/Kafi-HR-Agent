"""Education document verification — marks sheet / grade sheet institution checks."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_permission
from app.core.exceptions import ValidationFailed
from app.schemas.common import AuthContext
from app.schemas.education_verification import EducationVerificationResult
from app.services import audit_service
from app.services.education_verification_service import verify_education_documents

router = APIRouter(prefix="/education-documents", tags=["education-documents"])


async def _load_upload(upload: UploadFile | None) -> tuple[bytes | None, str | None, str | None]:
    if upload is None or not (upload.filename or "").strip():
        return None, None, None
    data = await upload.read()
    if not data:
        raise ValidationFailed(f"{upload.filename} is empty")
    return data, upload.filename, upload.content_type


@router.post("/verify", response_model=EducationVerificationResult)
async def verify_education_documents_endpoint(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
    marks_sheet: Annotated[UploadFile | None, File()] = None,
    grade_sheet: Annotated[UploadFile | None, File()] = None,
) -> EducationVerificationResult:
    """AI-assisted read of marks/grade sheets + plausibility check that named institutions exist."""
    marks_bytes, marks_name, marks_mime = await _load_upload(marks_sheet)
    grade_bytes, grade_name, grade_mime = await _load_upload(grade_sheet)

    result = verify_education_documents(
        marks_sheet_bytes=marks_bytes,
        marks_sheet_filename=marks_name,
        marks_sheet_mime=marks_mime,
        grade_sheet_bytes=grade_bytes,
        grade_sheet_filename=grade_name,
        grade_sheet_mime=grade_mime,
    )
    audit_service.log_from_auth(
        db,
        auth,
        action="employee.education_documents_verify",
        entity_type="education_verification",
        entity_id=0,
        after_state={
            "status": result.status,
            "verified": result.verified,
            "institution_count": len(result.institutions),
            "institutions_verified": [i.name for i in result.institutions if i.verified],
            "had_marks_sheet": bool(marks_bytes),
            "had_grade_sheet": bool(grade_bytes),
        },
    )
    return result
