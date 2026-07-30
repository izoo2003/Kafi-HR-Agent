"""KPI Pydantic schemas — FEATURE_KPI.md."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KpiDefinitionCreate(BaseModel):
    department_id: int
    name: str = Field(min_length=1)
    description: str | None = None
    measurement_unit: str | None = None
    target_value: Decimal
    weight: float = Field(gt=0, le=1)
    review_period: Literal["monthly", "quarterly", "annual"] = "monthly"


class KpiDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    measurement_unit: str | None = None
    target_value: Decimal | None = None
    weight: float | None = Field(default=None, gt=0, le=1)
    review_period: Literal["monthly", "quarterly", "annual"] | None = None


class KpiDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    name: str
    description: str | None
    measurement_unit: str | None
    target_value: Decimal | None
    weight: float | None
    review_period: str | None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime


class KpiEntryCreate(BaseModel):
    kpi_definition_id: int
    employee_id: int
    period_start: date
    period_end: date
    actual_value: Decimal
    notes: str | None = None


class KpiEntryUpdate(BaseModel):
    actual_value: Decimal | None = None
    notes: str | None = None


class KpiEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kpi_definition_id: int
    employee_id: int
    period_start: date
    period_end: date
    actual_value: Decimal
    score: float | None
    recorded_by: int
    notes: str | None
    created_at: datetime
    updated_at: datetime


class EmployeeKpiEntrySummary(BaseModel):
    kpi_definition_id: int
    name: str
    target: float
    actual: float
    score: float
    weight: float
    band: Literal["on_target", "at_risk", "below_target"]


class EmployeeKpiSummary(BaseModel):
    employee_id: int
    period_start: date
    period_end: date
    overall_score: float
    band: Literal["on_target", "at_risk", "below_target"]
    entries: list[EmployeeKpiEntrySummary]


class DepartmentKpiBreakdown(BaseModel):
    kpi_definition_id: int
    name: str
    average_score: float
    weight: float
    band: Literal["on_target", "at_risk", "below_target"]


class DepartmentKpiSummary(BaseModel):
    department_id: int
    period_start: date
    period_end: date
    overall_score: float
    band: Literal["on_target", "at_risk", "below_target"]
    entries_recorded: int
    entries_expected: int
    completeness: float
    employees: list[EmployeeKpiSummary]
    kpi_breakdown: list[DepartmentKpiBreakdown]


class MarkPeriodReviewedRequest(BaseModel):
    period_start: date
    period_end: date


class MarkPeriodReviewedResponse(BaseModel):
    message: str
    department_id: int
    period_start: date
    period_end: date
