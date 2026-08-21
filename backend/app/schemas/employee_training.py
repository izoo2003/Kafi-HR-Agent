"""Employee Development — training recommendation & assignment schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TrainingLevel = Literal["intermediate", "advanced"]
TrainingStatus = Literal["assigned", "in_progress", "completed"]


class TrainingCourseRecommendation(BaseModel):
    title: str
    level: TrainingLevel
    description: str
    provider: str | None = None
    url_hint: str | None = None


class EmployeeTrainingRecommendRequest(BaseModel):
    employee_id: int = Field(ge=1)
    topic: str = Field(min_length=3, max_length=500)


class EmployeeTrainingRecommendResponse(BaseModel):
    employee_id: int
    employee_name: str
    department_name: str | None = None
    role_title: str
    topic: str
    courses: list[TrainingCourseRecommendation]


class EmployeeTrainingAssignRequest(BaseModel):
    employee_id: int = Field(ge=1)
    topic: str = Field(min_length=3, max_length=500)
    courses: list[TrainingCourseRecommendation] = Field(min_length=1, max_length=10)


class EmployeeTrainingAssignmentRead(BaseModel):
    id: int
    employee_id: int
    employee_name: str | None = None
    employee_code: str | None = None
    title: str
    level: TrainingLevel
    description: str
    provider: str | None = None
    url_hint: str | None = None
    topic_prompt: str
    department_name: str | None = None
    role_title: str | None = None
    status: TrainingStatus
    assigned_by: int
    assigned_at: datetime
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeTrainingAssignResponse(BaseModel):
    items: list[EmployeeTrainingAssignmentRead]


class EmployeeTrainingListResponse(BaseModel):
    items: list[EmployeeTrainingAssignmentRead]
    total: int


class EmployeeTrainingStatusUpdate(BaseModel):
    status: TrainingStatus
