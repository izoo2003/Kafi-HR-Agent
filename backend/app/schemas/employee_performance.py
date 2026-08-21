"""Employee Development — monthly performance score schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PerformanceKpiEntryRead(BaseModel):
    id: int
    kpi_definition_id: int
    kpi_name: str
    measurement_unit: str | None = None
    target_value: Decimal | None = None
    weight: float | None = None
    period_start: date
    period_end: date
    actual_value: Decimal
    score: float | None = None
    notes: str | None = None
    created_at: datetime


class MonthlyPerformanceHistoryItem(BaseModel):
    period_year: int
    period_month: int
    label: str  # e.g. "May 2026"
    score_out_of_10: float
    entries_count: int
    finalized: bool = True
    ai_summary: str | None = None


class EmployeePerformanceRead(BaseModel):
    employee_id: int
    employee_name: str
    employee_code: str
    period_year: int
    period_month: int
    period_label: str
    is_current_month: bool
    is_finalized: bool
    score_out_of_10: float
    overall_pct: float | None = None
    entries_count: int
    entries: list[PerformanceKpiEntryRead] = []
    history: list[MonthlyPerformanceHistoryItem] = []
    ai_summary: str | None = None


class EmployeePerformanceAiSummaryRequest(BaseModel):
    employee_id: int
    period_year: int = Field(ge=2000, le=2100)
    period_month: int = Field(ge=1, le=12)


class EmployeePerformanceAiSummaryResponse(BaseModel):
    employee_id: int
    period_year: int
    period_month: int
    score_out_of_10: float
    ai_summary: str
