"""Shared shape every ingestion source (Gmail, Google Form, WhatsApp) must
produce. Keeping this uniform means the rest of the pipeline (parsing,
scoring, ranking) never needs to know where a CV came from.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.db.models import SourceChannel


@dataclass
class CandidateSubmission:
    full_name: str
    email: str
    phone: str | None
    location: str | None
    position_applied: str  # raw text as stated by the applicant/subject line
    source: SourceChannel
    source_ref: str  # gmail message id / sheet row id / whatsapp msg id
    cv_file_path: str  # local path to the saved CV file
    submitted_at: dt.datetime
    raw_context_text: str | None = None  # email subject+body / form free-text, for position inference


class CVIngestor:
    """Common interface every ingestion source implements."""

    source: SourceChannel

    def fetch_new_submissions(self) -> list[CandidateSubmission]:
        raise NotImplementedError
