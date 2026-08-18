"""KPI Pydantic schemas — FEATURE_KPI.md."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KpiDefinitionCreate(BaseModel):
    department_id: int | None = None
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
    owner_employee_id: int | None = None
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


class EmployeeWorkItem(BaseModel):
    text: str
    work_date: date | None = None
    points: float | None = None


class EmployeeKpiSummary(BaseModel):
    employee_id: int
    department_id: int
    period_start: date
    period_end: date
    submission_count: int
    contribution_score: float
    department_score: float
    department_band: Literal["on_target", "at_risk", "below_target", "complete"]
    global_score: float
    global_band: Literal["on_target", "at_risk", "below_target", "complete"]
    work_items: list[EmployeeWorkItem]


class DepartmentEmployeeKpiSummary(BaseModel):
    employee_id: int
    employee_name: str
    submission_count: int
    contribution_score: float
    band: Literal["on_target", "at_risk", "below_target", "complete"]
    work_items: list[EmployeeWorkItem]


class DepartmentKpiSummary(BaseModel):
    department_id: int
    period_start: date
    period_end: date
    overall_score: float
    band: Literal["on_target", "at_risk", "below_target", "complete"]
    entries_recorded: int
    entries_expected: int
    completeness: float
    employees: list[DepartmentEmployeeKpiSummary]


class GlobalDepartmentKpiSummary(BaseModel):
    department_id: int
    department_name: str
    overall_score: float
    band: Literal["on_target", "at_risk", "below_target", "complete"]
    entries_recorded: int
    entries_expected: int
    completeness: float


class GlobalKpiSummary(BaseModel):
    period_start: date
    period_end: date
    overall_score: float
    band: Literal["on_target", "at_risk", "below_target", "complete"]
    departments_complete: int
    departments_expected: int
    entries_recorded: int
    entries_expected: int
    completeness: float
    departments: list[GlobalDepartmentKpiSummary]


class KpiDailyPoint(BaseModel):
    date: date
    score: float
    band: Literal["on_target", "at_risk", "below_target", "complete"]
    entries_recorded: int


class KpiDailySummary(BaseModel):
    scope: Literal["global", "department"]
    department_id: int | None = None
    department_name: str | None = None
    period_start: date
    period_end: date
    overall_score: float
    band: Literal["on_target", "at_risk", "below_target", "complete"]
    days: list[KpiDailyPoint]


class KpiWorkLogRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    department_id: int
    department_name: str
    work_date: date
    text: str
    points: float
    created_at: datetime


class MarkPeriodReviewedRequest(BaseModel):
    period_start: date
    period_end: date


class MarkPeriodReviewedResponse(BaseModel):
    message: str
    department_id: int
    period_start: date
    period_end: date


class KpiAiSuggestRequest(BaseModel):
    department_id: int
    employee_id: int
    period_start: date
    period_end: date
    text: str = Field(min_length=3, max_length=4000)


class KpiAiSuggestResponse(BaseModel):
    kpi_definition_id: int | None = None
    actual_value: float | None = None
    formatted_work: str | None = None
    points_to_add: float | None = None
    reasoning: str


class KpiWorkSubmissionCreate(BaseModel):
    work_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    work_text: str = Field(min_length=3, max_length=8000)
    formatted_work: str | None = Field(default=None, max_length=8000)
    points_to_add: float | None = Field(default=None, ge=0, le=10)


class SeedDefaultsResponse(BaseModel):
    message: str
    created: list[KpiDefinitionRead]
    skipped_existing: list[str]
