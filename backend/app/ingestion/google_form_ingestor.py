"""Fetches CV submissions from the Google Form (design in
docs/google_form_field_spec.md) via its linked Google Sheet + Drive.

Google Forms with a "file upload" question write the uploaded file into a
Drive folder and put a link to it in the response Sheet. We read the sheet
with the Sheets API, then download the CV from Drive using the file id in
that link.

New-row tracking is done via a small local state file (last row index
processed) so re-running the pipeline doesn't re-download the same CVs.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

from app.config import BASE_DIR, settings
from app.db.models import SourceChannel
from app.ingestion.base import CandidateSubmission, CVIngestor
from app.ingestion.google_auth import get_credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
STATE_FILE = BASE_DIR / "data" / "google_form_state.json"
CV_STORAGE_DIR = BASE_DIR / "data" / "cv_files"

# Maps expected form fields -> possible header spellings in the sheet.
# Keep in sync with docs/google_form_field_spec.md.
HEADER_ALIASES = {
    "timestamp": ["timestamp"],
    "full_name": ["full name", "name"],
    "email": ["email address", "email"],
    "phone": ["phone number", "phone", "contact number"],
    "position": ["position applied for", "position", "role applied for"],
    "cv_upload": [
        "upload your cv",
        "upload your cv/resume",
        "cv upload",
        "resume upload",
        "cv/resume",
        "submit your cv",
        "submit your cv/resume",
        "submit your resume",
    ],
    "location": ["current location / city", "location", "city"],
}


class GoogleFormIngestor(CVIngestor):
    source = SourceChannel.GOOGLE_FORM

    def __init__(self) -> None:
        creds = get_credentials(
            settings.google_oauth_credentials_file, settings.google_form_token_file, SCOPES
        )
        self.sheets = build("sheets", "v4", credentials=creds)
        self.drive = build("drive", "v3", credentials=creds)

    def fetch_new_submissions(self) -> list[CandidateSubmission]:
        if not settings.google_form_sheet_id:
            raise RuntimeError(
                "GOOGLE_FORM_RESPONSES_SHEET_ID is not set in .env — link the Google Form's "
                "response Sheet ID first."
            )

        CV_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        rows = self._read_sheet_rows()
        if not rows:
            return []

        header_map = self._resolve_headers(rows[0])
        last_processed = self._load_last_processed_row()

        submissions: list[CandidateSubmission] = []
        new_last_processed = last_processed
        for row_idx, row in enumerate(rows[1:], start=2):  # sheet row numbers are 1-indexed w/ header
            if row_idx <= last_processed:
                continue
            new_last_processed = row_idx
            submission = self._row_to_submission(row_idx, row, header_map)
            if submission:
                submissions.append(submission)

        self._save_last_processed_row(new_last_processed)
        return submissions

    def _read_sheet_rows(self) -> list[list[str]]:
        sheet_name = self._first_sheet_title()
        result = (
            self.sheets.spreadsheets()
            .values()
            .get(spreadsheetId=settings.google_form_sheet_id, range=f"{sheet_name}!A:Z")
            .execute()
        )
        return result.get("values", [])

    def _first_sheet_title(self) -> str:
        """Resolves the actual tab name of the responses sheet rather than
        assuming Google Forms' default "Form Responses 1" — works
        regardless of what the tab was renamed to."""
        metadata = (
            self.sheets.spreadsheets()
            .get(spreadsheetId=settings.google_form_sheet_id, fields="sheets.properties.title")
            .execute()
        )
        sheets = metadata.get("sheets", [])
        if not sheets:
            raise RuntimeError("The linked Google Sheet has no tabs/sheets to read from.")
        return sheets[0]["properties"]["title"]

    def _resolve_headers(self, header_row: list[str]) -> dict[str, int]:
        """Matches sheet headers to expected fields via substring overlap
        (not exact equality) so wording variations like "Submit Your
        CV/Resume" vs "Upload your CV/Resume" still resolve correctly."""
        normalized = [h.strip().lower() for h in header_row]
        resolved: dict[str, int] = {}
        for field, aliases in HEADER_ALIASES.items():
            best_idx, best_len = None, 0
            for idx, header in enumerate(normalized):
                for alias in aliases:
                    if alias in header or header in alias:
                        if len(alias) > best_len:
                            best_idx, best_len = idx, len(alias)
            if best_idx is not None:
                resolved[field] = best_idx
        return resolved

    def _cell(self, row: list[str], header_map: dict[str, int], field: str) -> str:
        idx = header_map.get(field)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    def _row_to_submission(
        self, row_idx: int, row: list[str], header_map: dict[str, int]
    ) -> CandidateSubmission | None:
        cv_link = self._cell(row, header_map, "cv_upload")
        file_id = self._extract_drive_file_id(cv_link)
        if not file_id:
            return None  # no CV attached to this response — nothing to score

        cv_path = self._download_drive_file(file_id, row_idx)
        if not cv_path:
            return None

        return CandidateSubmission(
            full_name=self._cell(row, header_map, "full_name") or "Unknown",
            email=self._cell(row, header_map, "email").lower(),
            phone=self._cell(row, header_map, "phone") or None,
            location=self._cell(row, header_map, "location") or None,
            position_applied=self._cell(row, header_map, "position") or "Unspecified",
            source=self.source,
            source_ref=f"form_row_{row_idx}",
            cv_file_path=str(cv_path),
            submitted_at=self._parse_timestamp(self._cell(row, header_map, "timestamp")),
            raw_context_text=None,
        )

    def _extract_drive_file_id(self, link: str) -> str | None:
        if not link:
            return None
        match = re.search(r"[-\w]{25,}", link)
        return match.group(0) if match else None

    def _download_drive_file(self, file_id: str, row_idx: int) -> Path | None:
        try:
            metadata = self.drive.files().get(fileId=file_id, fields="name").execute()
            filename = metadata.get("name", f"{file_id}.pdf")
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
            dest = CV_STORAGE_DIR / f"form_row{row_idx}_{safe_name}"

            request = self.drive.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

            dest.write_bytes(buffer.getvalue())
            return dest
        except Exception:
            return None

    def _parse_timestamp(self, raw: str) -> dt.datetime:
        for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return dt.datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return dt.datetime.now(dt.UTC)

    def _load_last_processed_row(self) -> int:
        if not STATE_FILE.exists():
            return 1  # header is row 1
        try:
            return json.loads(STATE_FILE.read_text()).get("last_processed_row", 1)
        except (json.JSONDecodeError, OSError):
            return 1

    def _save_last_processed_row(self, row_idx: int) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({"last_processed_row": row_idx}), encoding="utf-8")
