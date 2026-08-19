"""Job description & scoring criteria schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _linkedin_feed_url(post_urn: str | None) -> str | None:
    raw = (post_urn or "").strip()
    if not raw or raw.lower() == "posted":
        return None
    if "/posts/" in raw:
        raw = raw.split("/posts/")[-1]
    raw = raw.strip().strip("/")
    if raw.isdigit():
        raw = f"urn:li:share:{raw}"
    if not raw.startswith("urn:li:"):
        return None
    return f"https://www.linkedin.com/feed/update/{raw}"


class LinkedInAccountPublic(BaseModel):
    name: str
    label: str


class LinkedInPostResult(BaseModel):
    account: str
    label: str | None = None
    author_urn: str | None = None
    post_urn: str | None = None
    post_url: str | None = None
    posted_at: datetime | str | None = None
    error: str | None = None

    @model_validator(mode="after")
    def _ensure_post_url(self) -> LinkedInPostResult:
        if not self.post_url:
            self.post_url = _linkedin_feed_url(self.post_urn)
        return self


class JobDescriptionCreate(BaseModel):
    title: str = Field(min_length=1)
    department_id: int
    description_text: str = Field(min_length=1)
    requirements_text: str | None = None
    status: Literal["draft", "open", "closed"] = "draft"
    # Names from GET /job-descriptions/linkedin-accounts. Empty = save Open without posting.
    linkedin_account_names: list[str] = Field(default_factory=list)


class JobPostingAiDraftRequest(BaseModel):
    title: str = Field(min_length=1)
    department_id: int


class JobPostingAiDraftSkill(BaseModel):
    name: str
    level: int = Field(ge=1, le=10)


class JobPostingAiDraftResult(BaseModel):
    description_text: str
    requirements_text: str
    skills: list[JobPostingAiDraftSkill] = []
    application_form_url: str | None = None


class JobDescriptionUpdate(BaseModel):
    title: str | None = None
    department_id: int | None = None
    description_text: str | None = None
    requirements_text: str | None = None
    status: Literal["draft", "open", "closed"] | None = None
    file_path: str | None = None
    linkedin_account_names: list[str] | None = None


class JobDescriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department_id: int
    description_text: str
    requirements_text: str | None
    file_path: str | None
    image_paths: list[str] = Field(default_factory=list)
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    applicants_count: int = 0
    application_form_url: str | None = None
    linkedin_posts: list[LinkedInPostResult] = Field(default_factory=list)

    @field_validator("linkedin_posts", mode="before")
    @classmethod
    def _linkedin_posts(cls, value: object) -> object:
        return value or []

    @field_validator("image_paths", mode="before")
    @classmethod
    def _image_paths(cls, value: object) -> object:
        if not value:
            return []
        if isinstance(value, list):
            return [str(v) for v in value if str(v).strip()]
        return []


class ScoringCriteriaCreate(BaseModel):
    criterion_name: str = Field(min_length=1)
    # Proficiency level 1–10 (1 = very low, 10 = expert). Scorer normalizes across skills.
    weight: float = Field(ge=1, le=10)
    scoring_rules: dict[str, Any]


class ScoringCriteriaUpdate(BaseModel):
    criterion_name: str | None = None
    weight: float | None = Field(default=None, ge=1, le=10)
    scoring_rules: dict[str, Any] | None = None


class ScoringCriteriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_description_id: int
    criterion_name: str
    weight: float
    scoring_rules: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class ScoringCriteriaReplace(BaseModel):
    """Replace all skills for a job. Each weight is a proficiency level 1–10 (1=very low, 10=expert)."""

    criteria: list[ScoringCriteriaCreate]
