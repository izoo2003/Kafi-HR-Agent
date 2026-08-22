"""Education document verification request/response schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EducationDocumentSummary(BaseModel):
    document_type: Literal["marks_sheet", "grade_sheet", "unknown"] = "unknown"
    readable: bool = False
    looks_like_education_document: bool = False
    student_name: str | None = None
    program_or_degree: str | None = None
    board_or_university: str | None = None
    notes: str | None = None


class EducationInstitutionCheck(BaseModel):
    name: str
    institution_type: Literal["school", "college", "university", "board", "other"] = "other"
    country: str | None = None
    city: str | None = None
    verified: bool = Field(
        description="True when AI confirms this is a real, known institution.",
    )
    confidence: Literal["high", "medium", "low"] = "low"
    verification_note: str = ""
    source_hint: str | None = Field(
        default=None,
        description="Brief note on how existence was assessed (e.g. known public institution).",
    )


class EducationVerificationChecks(BaseModel):
    documents_provided: int = 0
    documents_readable: bool = False
    looks_like_education_documents: bool = False
    all_institutions_verified: bool = False
    any_institution_verified: bool = False


class EducationVerificationResult(BaseModel):
    status: Literal[
        "verified",
        "partial",
        "unverified",
        "unreadable",
        "not_education_document",
        "needs_documents",
    ]
    verified: bool = Field(
        description="True when every identified institution is verified as a real place.",
    )
    message: str
    documents: list[EducationDocumentSummary] = Field(default_factory=list)
    institutions: list[EducationInstitutionCheck] = Field(default_factory=list)
    checks: EducationVerificationChecks
    disclaimer: str
