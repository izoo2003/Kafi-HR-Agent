"""Generates and serves the formatted Excel reports for download."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.reporting.excel_report import generate_master_report, generate_position_report

router = APIRouter(prefix="/reports", tags=["reports"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"}


@router.get("/master")
def download_master_report(db: Session = Depends(get_db)) -> FileResponse:
    """Fresh master workbook with Why Select / Why Reject for every candidate."""
    path = generate_master_report(db)
    return FileResponse(
        path,
        media_type=XLSX_MEDIA_TYPE,
        filename=path.name,
        headers=NO_CACHE,
    )


@router.get("/positions/{position}")
def download_position_report(position: str, db: Session = Depends(get_db)) -> FileResponse:
    path = generate_position_report(db, position)
    return FileResponse(
        path,
        media_type=XLSX_MEDIA_TYPE,
        filename=path.name,
        headers=NO_CACHE,
    )
