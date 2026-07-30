"""Fetches CV submissions sent as attachments to hr@kafi-group.com via the
Gmail API.

Each processed email gets a Gmail label ("HR-Agent-Processed") applied so
re-running the pipeline never re-downloads/re-scores the same email.
Position applied for is taken from the subject line (best-effort) and
refined later by `position_matcher` against configured role profiles.
"""
from __future__ import annotations

import base64
import datetime as dt
import email.utils
import re
from pathlib import Path

from googleapiclient.discovery import build

from app.config import BASE_DIR, settings
from app.db.models import SourceChannel
from app.ingestion.base import CandidateSubmission, CVIngestor
from app.ingestion.google_auth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
PROCESSED_LABEL = "HR-Agent-Processed"
CV_EXTENSIONS = {".pdf", ".docx"}
CV_STORAGE_DIR = BASE_DIR / "data" / "cv_files"


class GmailIngestor(CVIngestor):
    source = SourceChannel.GMAIL

    def __init__(self) -> None:
        creds = get_credentials(
            settings.google_oauth_credentials_file, settings.google_oauth_token_file, SCOPES
        )
        self.service = build("gmail", "v1", credentials=creds)
        self._label_id = self._ensure_processed_label()

    def _ensure_processed_label(self) -> str:
        labels = self.service.users().labels().list(userId="me").execute().get("labels", [])
        for label in labels:
            if label["name"] == PROCESSED_LABEL:
                return label["id"]
        created = (
            self.service.users()
            .labels()
            .create(userId="me", body={"name": PROCESSED_LABEL})
            .execute()
        )
        return created["id"]

    def fetch_new_submissions(self) -> list[CandidateSubmission]:
        CV_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        # Cap how far back / how many messages we scan per run. Without this,
        # a busy inbox with many unlabeled attachments can hang "Run Full
        # Pipeline" for several minutes and freeze the API.
        query = (
            f"to:{settings.gmail_address} has:attachment "
            f"-label:{PROCESSED_LABEL} newer_than:30d"
        )
        submissions: list[CandidateSubmission] = []
        max_messages = 20
        processed = 0

        request = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_messages)
        )
        while request is not None and processed < max_messages:
            response = request.execute()
            for msg_meta in response.get("messages", []):
                if processed >= max_messages:
                    break
                submission = self._process_message(msg_meta["id"])
                if submission:
                    submissions.append(submission)
                self._mark_processed(msg_meta["id"])
                processed += 1
            request = self.service.users().messages().list_next(request, response)

        return submissions

    def _mark_processed(self, message_id: str) -> None:
        self.service.users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": [self._label_id]}
        ).execute()

    def _process_message(self, message_id: str) -> CandidateSubmission | None:
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        headers = {h["name"]: h["value"] for h in message["payload"].get("headers", [])}
        sender_name, sender_email = email.utils.parseaddr(headers.get("From", ""))
        subject = headers.get("Subject", "")
        body_text = self._extract_body_text(message["payload"])

        cv_path = self._download_first_cv_attachment(message_id, message["payload"])
        if not cv_path:
            return None  # no usable CV attachment on this email — skip, still gets labeled

        return CandidateSubmission(
            full_name=sender_name.strip() or sender_email.split("@")[0],
            email=sender_email.strip().lower(),
            phone=self._extract_phone(body_text),
            location=None,
            position_applied=subject.strip() or "Unspecified",
            source=self.source,
            source_ref=message_id,
            cv_file_path=str(cv_path),
            submitted_at=self._parse_date(headers.get("Date")),
            raw_context_text=f"Subject: {subject}\n\n{body_text}",
        )

    def _download_first_cv_attachment(self, message_id: str, payload: dict) -> Path | None:
        for part in self._iter_parts(payload):
            filename = part.get("filename", "")
            if not filename:
                continue
            suffix = Path(filename).suffix.lower()
            if suffix not in CV_EXTENSIONS:
                continue

            body = part.get("body", {})
            attachment_id = body.get("attachmentId")
            data = body.get("data")

            if attachment_id and not data:
                attachment = (
                    self.service.users()
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
            dest = CV_STORAGE_DIR / f"gmail_{message_id}_{safe_name}"
            dest.write_bytes(file_bytes)
            return dest

        return None

    def _iter_parts(self, payload: dict):
        if "parts" in payload:
            for part in payload["parts"]:
                yield from self._iter_parts(part)
        else:
            yield payload

    def _extract_body_text(self, payload: dict) -> str:
        for part in self._iter_parts(payload):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    def _extract_phone(self, text: str) -> str | None:
        match = re.search(r"(\+?\d[\d\s\-]{8,14}\d)", text)
        return match.group(1).strip() if match else None

    def _parse_date(self, raw_date: str | None) -> dt.datetime:
        if not raw_date:
            return dt.datetime.now(dt.UTC)
        try:
            return email.utils.parsedate_to_datetime(raw_date)
        except (TypeError, ValueError):
            return dt.datetime.now(dt.UTC)
