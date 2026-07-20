"""Orchestrates the full CV ranking flow: ingest -> parse -> score -> rank ->
report. Each stage is also callable independently from the CLI so you can
re-run just scoring, or just reporting, without re-fetching everything.
"""
from __future__ import annotations

import datetime as dt
import json
import logging

from sqlalchemy.orm import Session

from app.db.models import Application, ApplicationStatus, Candidate, SourceChannel
from app.ingestion.base import CandidateSubmission
from app.ingestion.gmail_ingestor import GmailIngestor
from app.ingestion.google_form_ingestor import GoogleFormIngestor
from app.ingestion.position_matcher import match_position
from app.ingestion.whatsapp_ingestor import WhatsAppIngestor
from app.config import load_role_profiles
from app.parsing.cv_parser import extract_text
from app.ranking.ranker import list_positions, recompute_ranks
from app.reporting.excel_report import generate_master_report, generate_position_report
from app.scoring.gemini_scorer import score_cv

logger = logging.getLogger(__name__)

INGESTORS = {
    SourceChannel.GMAIL: GmailIngestor,
    SourceChannel.GOOGLE_FORM: GoogleFormIngestor,
    SourceChannel.WHATSAPP: WhatsAppIngestor,
}


def fetch_submissions(session: Session, sources: list[SourceChannel] | None = None) -> int:
    """Fetches new submissions from the given sources (default: all) and
    persists them as candidates/applications. Returns count of new
    applications created."""
    sources = sources or list(INGESTORS.keys())
    role_profiles = load_role_profiles()
    created = 0

    for source in sources:
        ingestor_cls = INGESTORS[source]
        try:
            ingestor = ingestor_cls()
        except Exception as exc:
            logger.warning("Skipping %s ingestion — not configured yet: %s", source.value, exc)
            continue

        submissions = ingestor.fetch_new_submissions()
        for submission in submissions:
            # Match known roles against the full email/form context, but if
            # nothing matches, fall back to the short subject/field value —
            # never title-case the entire email body into a position name.
            submission.position_applied = match_position(
                submission.raw_context_text or submission.position_applied,
                role_profiles,
                fallback_label=submission.position_applied,
            )
            if _persist_submission(session, submission):
                created += 1

    return created


def _persist_submission(session: Session, submission: CandidateSubmission) -> bool:
    candidate = session.query(Candidate).filter_by(email=submission.email).one_or_none()
    if candidate is None:
        candidate = Candidate(
            full_name=submission.full_name,
            email=submission.email,
            phone=submission.phone,
            location=submission.location,
        )
        session.add(candidate)
        session.flush()

    existing = (
        session.query(Application)
        .filter_by(
            candidate_id=candidate.id,
            position_applied=submission.position_applied,
            source=submission.source,
        )
        .one_or_none()
    )
    if existing:
        return False  # already have this exact application on file

    application = Application(
        candidate_id=candidate.id,
        position_applied=submission.position_applied,
        source=submission.source,
        source_ref=submission.source_ref,
        cv_file_path=submission.cv_file_path,
        status=ApplicationStatus.RECEIVED,
        submitted_at=submission.submitted_at,
    )
    session.add(application)
    return True


def parse_and_score_pending(session: Session, retry_failed: bool = False) -> tuple[int, int]:
    """Parses CV text + scores every application not yet scored. Returns
    (succeeded_count, failed_count).

    By default skips previously FAILED rows (so Run Full Pipeline does not
    keep re-hitting Gemini on broken/empty CVs). Pass retry_failed=True to
    include them again.
    """
    statuses = [ApplicationStatus.RECEIVED, ApplicationStatus.PARSED]
    if retry_failed:
        statuses.append(ApplicationStatus.FAILED)

    pending = (
        session.query(Application)
        .filter(Application.status.in_(statuses))
        .all()
    )

    succeeded, failed = 0, 0
    for application in pending:
        try:
            if not application.cv_raw_text:
                application.cv_raw_text = extract_text(application.cv_file_path)
                application.status = ApplicationStatus.PARSED

            result = score_cv(application.cv_raw_text, application.position_applied)
            application.score = result.score
            application.verdict = result.verdict.label
            application.education_summary = result.education_summary
            application.experience_summary = result.experience_summary
            application.key_strengths_json = json.dumps(result.key_strengths)
            application.hiring_summary = result.hiring_summary
            application.status = ApplicationStatus.SCORED
            application.scored_at = dt.datetime.now(dt.UTC)
            succeeded += 1
        except Exception as exc:
            logger.exception("Failed to score application %s", application.id)
            application.status = ApplicationStatus.FAILED
            application.error_message = str(exc)
            failed += 1

    return succeeded, failed


def rank_all(session: Session) -> None:
    recompute_ranks(session)


def generate_all_reports(session: Session) -> list[str]:
    paths = []
    for position in list_positions(session):
        paths.append(str(generate_position_report(session, position)))
    paths.append(str(generate_master_report(session)))
    return paths


def run_full_pipeline(session: Session) -> dict:
    created = fetch_submissions(session)
    succeeded, failed = parse_and_score_pending(session)
    rank_all(session)
    reports = generate_all_reports(session)
    return {
        "new_applications": created,
        "scored": succeeded,
        "failed": failed,
        "reports": reports,
    }
