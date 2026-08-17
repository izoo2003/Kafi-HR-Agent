"""CNIC verification request/response schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CnicExtractedFields(BaseModel):
    cnic: str | None = None
    full_name: str | None = None
    father_name: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    address: str | None = None
    notes: str | None = None


class CnicVerificationChecks(BaseModel):
    format_valid: bool = False
    image_provided: bool = False
    image_readable: bool = False
    looks_like_pakistan_cnic: bool = False
    cnic_match: bool = False


class CnicVerificationResult(BaseModel):
    status: Literal[
        "verified",
        "mismatch",
        "invalid_format",
        "unreadable",
        "not_cnic_document",
        "needs_image",
    ]
    authentic: bool = Field(
        description="True only when format is valid and typed CNIC matches OCR from the card image.",
    )
    message: str
    typed_cnic: str
    extracted: CnicExtractedFields | None = None
    checks: CnicVerificationChecks
    disclaimer: str
