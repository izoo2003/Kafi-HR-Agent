"""Shared shape every automated CV source (Gmail, Google Form) produces.

Keeping this uniform means downstream code (dedupe, storage, matching,
pipeline) never needs to know where a CV came from — see
FEATURE_CV_SCREENING.md §11.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

CvSource = Literal["gmail", "google_form"]


@dataclass
class CvSubmission:
    full_name: str
    email: str | None
    phone: str | None
    position_hint: str  # raw text as stated by the applicant (subject line / form field)
    source: CvSource
    source_ref: str  # gmail message id / form row id — dedupe key
    cv_filename: str
    cv_bytes: bytes
    submitted_at: dt.datetime
    raw_context_text: str | None = None  # email subject+body / form free-text


@dataclass
class SourceFetchResult:
    """Per-source outcome for a sync run — never raises past this boundary."""

    source: CvSource
    configured: bool
    submissions: list[CvSubmission]
    message: str | None = None  # e.g. "Gmail not connected — add OAuth credentials"
