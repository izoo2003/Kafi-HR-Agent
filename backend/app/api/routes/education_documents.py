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


async def _load_uploads(uploads: list[UploadFile]) -> list[tuple[bytes, str, str | None]]:
    loaded: list[tuple[bytes, str, str | None]] = []
    for upload in uploads:
        if upload is None or not (upload.filename or "").strip():
            continue
        data = await upload.read()
        if not data:
            raise ValidationFailed(f"{upload.filename} is empty")
        loaded.append((data, upload.filename or "document", upload.content_type))
    return loaded


@router.post("/verify", response_model=EducationVerificationResult)
async def verify_education_documents_endpoint(
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
    documents: Annotated[list[UploadFile] | None, File()] = None,
) -> EducationVerificationResult:
    """AI-assisted read of education documents + plausibility check that named institutions exist."""
    uploads = await _load_uploads(documents or [])
    result = verify_education_documents(uploads=uploads)
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
            "documents_provided": result.checks.documents_provided,
        },
    )
    return result
