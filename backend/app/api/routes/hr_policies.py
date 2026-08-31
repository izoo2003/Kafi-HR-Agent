"""HR policies — readable by any signed-in user; writable by employees write."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user, require_permission
from app.schemas.common import AuthContext
from app.schemas.hr_policies import HrPoliciesDocument
from app.services import hr_policy_service

router = APIRouter(tags=["hr-policies"])


@router.get("/hr-policies", response_model=HrPoliciesDocument)
def get_hr_policies(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthContext, Depends(get_current_user)],
) -> HrPoliciesDocument:
    return hr_policy_service.get_hr_policies(db)


@router.put("/hr-policies", response_model=HrPoliciesDocument)
def put_hr_policies(
    payload: HrPoliciesDocument,
    db: Annotated[Session, Depends(get_db)],
    auth: Annotated[AuthContext, Depends(require_permission("employees", "write"))],
) -> HrPoliciesDocument:
    return hr_policy_service.save_hr_policies(db, auth, payload)
