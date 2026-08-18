"""Fetches CV submissions sent as attachments to the HR inbox via the Gmail
API — FEATURE_CV_SCREENING.md §11.

Each processed email gets a Gmail label ("HR-Agent-Processed") applied so
re-running sync never re-downloads the same email (a secondary safety net —
the primary dedupe is the (source, source_ref) check in cv_screening_service).
Position hint is taken from the subject line; the AI/keyword matcher in
scoring/cv_job_matcher.py resolves it to an actual job description.
"""
from __future__ import annotations

import base64
import datetime as dt
import email.utils
import logging
import re

from app.core.config import Settings
from app.ingestion.cv_classifier import CV_EXTENSIONS, AttachmentCandidate, pick_cv_attachment
from app.ingestion.cv_submission import CvSubmission, SourceFetchResult
from app.ingestion.google_auth import GoogleCredentialsNotConfigured, get_credentials

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
PROCESSED_LABEL = "HR-Agent-Processed"
MAX_MESSAGES_PER_RUN = 20


def fetch_gmail_submissions(settings: Settings) -> SourceFetchResult:
    """Never raises — returns a SourceFetchResult describing what happened,
    including the "not configured" / "connection failed" cases."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return SourceFetchResult(
            source="gmail",
            configured=False,
            submissions=[],
            message="Gmail sync requires google-api-python-client — check backend/requirements.txt install.",
        )

    creds_path = settings.resolved_path(settings.google_oauth_credentials_file)
    token_path = settings.resolved_path(settings.google_oauth_token_file)

    try:
        creds = get_credentials(creds_path, token_path, SCOPES, purpose="Gmail")
    except GoogleCredentialsNotConfigured as exc:
        return SourceFetchResult(
            source="gmail", configured=False, submissions=[], message=str(exc)
        )
    except Exception as exc:  # noqa: BLE001 — any auth failure is "not connected", not a crash
        logger.warning("Gmail auth failed: %s", exc)
        return SourceFetchResult(
            source="gmail",
            configured=False,
            submissions=[],
            message=f"Gmail authentication failed: {exc}",
        )

    try:
        service = build("gmail", "v1", credentials=creds)
        label_id = _ensure_processed_label(service)
        submissions = _fetch_messages(service, settings, label_id)
        return SourceFetchResult(source="gmail", configured=True, submissions=submissions)
    except Exception as exc:  # noqa: BLE001 — never let a Gmail API hiccup break the whole sync
        logger.exception("Gmail fetch failed")
        return SourceFetchResult(
            source="gmail",
            configured=True,
            submissions=[],
            message=f"Gmail fetch failed: {exc}",
        )


def _ensure_processed_label(service) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in labels:
        if label["name"] == PROCESSED_LABEL:
            return label["id"]
    created = (
        service.users().labels().create(userId="me", body={"name": PROCESSED_LABEL}).execute()
    )
    return created["id"]


def _fetch_messages(service, settings: Settings, label_id: str) -> list[CvSubmission]:
    query = (
        f"to:{settings.gmail_address} has:attachment "
        f"-label:{PROCESSED_LABEL} newer_than:30d"
    )
    submissions: list[CvSubmission] = []
    processed = 0

    request = service.users().messages().list(userId="me", q=query, maxResults=MAX_MESSAGES_PER_RUN)
    while request is not None and processed < MAX_MESSAGES_PER_RUN:
        response = request.execute()
        for msg_meta in response.get("messages", []):
            if processed >= MAX_MESSAGES_PER_RUN:
                break
            submission = _process_message(service, msg_meta["id"], settings)
            if submission:
                submissions.append(submission)
            _mark_processed(service, msg_meta["id"], label_id)
            processed += 1
        request = service.users().messages().list_next(request, response)

    return submissions


def _mark_processed(service, message_id: str, label_id: str) -> None:
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": [label_id]}
    ).execute()


def _process_message(service, message_id: str, settings: Settings) -> CvSubmission | None:
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}
    sender_name, sender_email = email.utils.parseaddr(headers.get("From", ""))
    subject = headers.get("Subject", "")
    body_text = _extract_body_text(message["payload"])

    filename, cv_bytes = _download_best_cv_attachment(
        service, message_id, message["payload"], settings
    )
    if cv_bytes is None:
        return None  # no usable CV attachment — skip, still gets labeled

    return CvSubmission(
        full_name=sender_name.strip() or sender_email.split("@")[0],
        email=sender_email.strip().lower() or None,
        phone=_extract_phone(body_text),
        position_hint=subject.strip() or "Unspecified",
        source="gmail",
        source_ref=message_id,
        cv_filename=filename or f"gmail_{message_id}.pdf",
        cv_bytes=cv_bytes,
        submitted_at=_parse_date(headers.get("Date")),
        raw_context_text=f"Subject: {subject}\n\n{body_text}",
    )


def _download_best_cv_attachment(
    service, message_id: str, payload: dict, settings: Settings
) -> tuple[str | None, bytes | None]:
    candidates: list[AttachmentCandidate] = []
    for part in _iter_parts(payload):
        filename = part.get("filename", "")
        if not filename:
            continue
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in CV_EXTENSIONS:
            continue

        headers = {h["name"].lower(): h["value"] for h in part.get("headers", []) or []}
        disp = (headers.get("content-disposition") or "").lower()
        has_cid = bool(headers.get("content-id"))
        is_inline = disp.startswith("inline") or (has_cid and "attachment" not in disp)

        body = part.get("body", {})
        attachment_id = body.get("attachmentId")
        data = body.get("data")

        if attachment_id and not data:
            attachment = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )
            data = attachment["data"]

        if not data:
            continue

        file_bytes = base64.urlsafe_b64decode(data)
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
        candidates.append(
            AttachmentCandidate(filename=safe_name, content=file_bytes, is_inline=is_inline)
        )
    return pick_cv_attachment(candidates, settings, source="email")


def _iter_parts(payload: dict):
    if "parts" in payload:
        for part in payload["parts"]:
            yield from _iter_parts(part)
    else:
        yield payload


def _extract_body_text(payload: dict) -> str:
    for part in _iter_parts(payload):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    return ""


def _extract_phone(text: str) -> str | None:
    match = re.search(r"(\+?\d[\d\s\-]{8,14}\d)", text)
    return match.group(1).strip() if match else None


def _parse_date(raw_date: str | None) -> dt.datetime:
    if not raw_date:
        return dt.datetime.now(dt.timezone.utc)
    try:
        return email.utils.parsedate_to_datetime(raw_date)
    except (TypeError, ValueError):
        return dt.datetime.now(dt.timezone.utc)


def restore_gmail_cv(message_id: str, settings: Settings) -> tuple[str, bytes] | None:
    """Re-download a previously ingested Gmail CV by message id."""
    if not (message_id or "").strip():
        return None
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None
    creds_path = settings.resolved_path(settings.google_oauth_credentials_file)
    token_path = settings.resolved_path(settings.google_oauth_token_file)
    try:
        creds = get_credentials(creds_path, token_path, SCOPES, purpose="Gmail")
        service = build("gmail", "v1", credentials=creds)
        submission = _process_message(service, message_id.strip(), settings)
    except Exception:
        logger.warning("Gmail CV restore failed for %s", message_id, exc_info=True)
        return None
    if submission and submission.cv_bytes:
        return submission.cv_filename, submission.cv_bytes
    return None
