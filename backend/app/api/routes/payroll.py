"""Payroll — skeleton."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import require_permission
from app.schemas.common import AuthContext, MessageResponse

router = APIRouter(tags=["payroll"])


@router.get("/payroll-runs", response_model=MessageResponse)
def list_payroll_runs(
    _: Annotated[AuthContext, Depends(require_permission("payroll", "read"))],
) -> MessageResponse:
    return MessageResponse(message="Payroll module scaffolded — implement with FEATURE_PAYROLL.md.")
