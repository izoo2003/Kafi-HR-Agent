"""Fetches CV submissions from the Google Form via its linked response Sheet
+ Drive — FEATURE_CV_SCREENING.md §11.

Google Forms with a "file upload" question write the uploaded file into a
Drive folder and put a link to it in the response Sheet. We read the sheet
with the Sheets API, then download the CV from Drive using the file id in
that link. New-row tracking uses a small local state file (last row index
processed) so re-running sync doesn't re-download the same CVs.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import logging
import re

from app.core.config import Settings
from app.ingestion.cv_classifier import classify_cv_document
from app.ingestion.cv_submission import CvSubmission, SourceFetchResult
from app.ingestion.google_auth import GoogleCredentialsNotConfigured, get_credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Maps expected form fields -> possible header spellings in the sheet.
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
}


def fetch_form_submissions(settings: Settings) -> SourceFetchResult:
    """Never raises — returns a SourceFetchResult describing what happened."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return SourceFetchResult(
            source="google_form",
            configured=False,
            submissions=[],
            message="Google Form sync requires google-api-python-client — check backend/requirements.txt install.",
        )

    if not settings.google_form_sheet_id:
        return SourceFetchResult(
            source="google_form",
            configured=False,
            submissions=[],
            message="GOOGLE_FORM_RESPONSES_SHEET_ID is not set — link the Google Form's response Sheet ID first.",
        )

    creds_path = settings.resolved_path(settings.google_oauth_credentials_file)
    token_path = settings.resolved_path(settings.google_form_token_file)

    try:
        creds = get_credentials(
            creds_path, token_path, SCOPES, purpose="Google Form"
        )
    except GoogleCredentialsNotConfigured as exc:
        return SourceFetchResult(
            source="google_form", configured=False, submissions=[], message=str(exc)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google Form auth failed: %s", exc)
        return SourceFetchResult(
            source="google_form",
            configured=False,
            submissions=[],
            message=f"Google Form authentication failed: {exc}",
        )

    try:
        sheets = build("sheets", "v4", credentials=creds)
        drive = build("drive", "v3", credentials=creds)
        submissions, row_warnings = _fetch_new_rows(sheets, drive, settings)
        message = "; ".join(row_warnings[:4]) if row_warnings else None
        if row_warnings and len(row_warnings) > 4:
            message = f"{message}; +{len(row_warnings) - 4} more"
        return SourceFetchResult(
            source="google_form",
            configured=True,
            submissions=submissions,
            message=message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Google Form fetch failed")
        message = f"Google Form fetch failed: {exc}"
        if "403" in str(exc) or "does not have permission" in str(exc).lower():
            message = (
                "Google Form fetch failed: the authenticated Google account does not have access "
                "to the linked response spreadsheet or uploaded CV files. Re-authorize with the "
                "Google account that owns the form/spreadsheet, or share the response sheet and "
                "Drive upload folder with the configured service account."
            )
        return SourceFetchResult(
            source="google_form",
            configured=True,
            submissions=[],
            message=message,
        )


def _state_file(settings: Settings):
    return settings.data_dir / "google_form_state.json"


def _max_rows_per_run(settings: Settings) -> int:
    return int(getattr(settings, "cv_sync_batch_size", 20) or 20)


def _fetch_new_rows(sheets, drive, settings: Settings) -> tuple[list[CvSubmission], list[str]]:
    sheet_id = settings.google_form_sheet_id
    sheet_name = _first_sheet_title(sheets, sheet_id)
    result = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=f"{sheet_name}!A:Z")
        .execute()
    )
    rows = result.get("values", [])
    if not rows:
        return [], []

    header_map = _resolve_headers(rows[0])
    processed_rows = _load_processed_rows(settings, sheet_row_count=len(rows))
    warnings: list[str] = []
    if "cv_upload" not in header_map:
        warnings.append(
            "response sheet is missing a CV upload column — expected a header like "
            "'Upload your CV' or 'Upload your CV/Resume'"
        )

    submissions: list[CvSubmission] = []
    imported_this_run = 0
    max_rows = _max_rows_per_run(settings)
    pending_row_indices = [
        row_idx for row_idx in range(2, len(rows) + 1) if row_idx not in processed_rows
    ]
    # Newest submissions live at the bottom of the sheet — prioritize them first.
    pending_row_indices.sort(reverse=True)

    for row_idx in pending_row_indices:
        if imported_this_run >= max_rows:
            warnings.append("more Google Form rows remain — click Sync CVs again")
            break
        row = rows[row_idx - 1]
        submission, skip_reason = _row_to_submission(drive, row_idx, row, header_map, settings)
        if submission:
            submissions.append(submission)
            processed_rows.add(row_idx)
            imported_this_run += 1
        elif skip_reason == "no_cv":
            processed_rows.add(row_idx)
        elif skip_reason:
            warnings.append(f"row {row_idx}: {skip_reason}")
            if not skip_reason.startswith("could not download"):
                processed_rows.add(row_idx)

    _save_processed_rows(settings, processed_rows)
    return submissions, warnings


def _first_sheet_title(sheets, sheet_id: str) -> str:
    """Resolves the actual tab name rather than assuming Google Forms'
    default "Form Responses 1" — works regardless of renames."""
    metadata = sheets.spreadsheets().get(
        spreadsheetId=sheet_id, fields="sheets.properties.title"
    ).execute()
    tabs = metadata.get("sheets", [])
    if not tabs:
        raise RuntimeError("The linked Google Sheet has no tabs/sheets to read from.")
    return tabs[0]["properties"]["title"]


def _resolve_headers(header_row: list[str]) -> dict[str, int]:
    """Matches sheet headers to expected fields via substring overlap (not
    exact equality) so wording variations still resolve correctly."""
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


def _cell(row: list[str], header_map: dict[str, int], field: str) -> str:
    idx = header_map.get(field)
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


def _row_to_submission(
    drive, row_idx: int, row: list[str], header_map: dict[str, int], settings: Settings
) -> tuple[CvSubmission | None, str | None]:
    cv_link = _cell(row, header_map, "cv_upload")
    file_id = _extract_drive_file_id(cv_link)
    if not file_id:
        return None, "no_cv" if not cv_link else "CV link in sheet could not be parsed"

    filename, cv_bytes = _download_drive_file(drive, file_id)
    if cv_bytes is None:
        return None, "could not download the uploaded CV from Google Drive — check file permissions"

    classification = classify_cv_document(
        filename=filename or "",
        content=cv_bytes,
        settings=settings,
        source="form",
    )
    if not classification.is_cv:
        return None, classification.reason

    email = _cell(row, header_map, "email").lower()
    return (
        CvSubmission(
            full_name=_cell(row, header_map, "full_name") or "Unknown",
            email=email or None,
            phone=_cell(row, header_map, "phone") or None,
            position_hint=_cell(row, header_map, "position") or "Unspecified",
            source="google_form",
            source_ref=f"form_row_{row_idx}",
            cv_filename=filename or f"form_row{row_idx}.pdf",
            cv_bytes=cv_bytes,
            submitted_at=_parse_timestamp(_cell(row, header_map, "timestamp")),
            raw_context_text=None,
        ),
        None,
    )


def _extract_drive_file_id(link: str) -> str | None:
    if not link:
        return None
    match = re.search(r"[-\w]{25,}", link)
    return match.group(0) if match else None


def _download_drive_file(drive, file_id: str) -> tuple[str | None, bytes | None]:
    try:
        metadata = drive.files().get(fileId=file_id, fields="name").execute()
        filename = metadata.get("name", f"{file_id}.pdf")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)

        from googleapiclient.http import MediaIoBaseDownload

        request = drive.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        return safe_name, buffer.getvalue()
    except Exception:  # noqa: BLE001 — one bad row shouldn't fail the whole sync
        logger.warning("Failed to download Drive file %s", file_id, exc_info=True)
        return None, None


def _parse_timestamp(raw: str) -> dt.datetime:
    for fmt in ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(raw, fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return dt.datetime.now(dt.timezone.utc)


def _load_processed_rows(settings: Settings, *, sheet_row_count: int) -> set[int]:
    state_file = _state_file(settings)
    if not state_file.exists():
        return set()
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return set()

    if "processed_rows" in data:
        rows: set[int] = set()
        for raw in data.get("processed_rows", []):
            try:
                rows.add(int(raw))
            except (TypeError, ValueError):
                continue
    else:
        # Migrate legacy last_processed_row checkpoints.
        last = int(data.get("last_processed_row", 1) or 1)
        rows = set(range(2, last + 1))

    if sheet_row_count > 1:
        rows = {row_idx for row_idx in rows if row_idx <= sheet_row_count}
    return rows


def _save_processed_rows(settings: Settings, processed_rows: set[int]) -> None:
    state_file = _state_file(settings)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    trimmed = sorted(processed_rows)[-5000:]
    state_file.write_text(json.dumps({"processed_rows": trimmed}), encoding="utf-8")


def restore_form_cv(source_ref: str, settings: Settings) -> tuple[str, bytes] | None:
    """Re-download a Google Form CV using form_row_{n} from the response sheet."""
    match = re.match(r"form_row_(\d+)$", (source_ref or "").strip())
    if not match or not settings.google_form_sheet_id:
        return None
    row_idx = int(match.group(1))
    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None
    creds_path = settings.resolved_path(settings.google_oauth_credentials_file)
    token_path = settings.resolved_path(settings.google_form_token_file)
    try:
        creds = get_credentials(creds_path, token_path, SCOPES, purpose="Google Form")
        sheets = build("sheets", "v4", credentials=creds)
        drive = build("drive", "v3", credentials=creds)
        sheet_id = settings.google_form_sheet_id
        sheet_name = _first_sheet_title(sheets, sheet_id)
        result = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=f"{sheet_name}!A:Z")
            .execute()
        )
        rows = result.get("values", [])
        if len(rows) < row_idx:
            return None
        header_map = _resolve_headers(rows[0])
        row = rows[row_idx - 1]
        cv_link = _cell(row, header_map, "cv_upload")
        file_id = _extract_drive_file_id(cv_link)
        if not file_id:
            return None
        filename, cv_bytes = _download_drive_file(drive, file_id)
    except Exception:
        logger.warning("Google Form CV restore failed for %s", source_ref, exc_info=True)
        return None
    if cv_bytes:
        return filename or f"form_row{row_idx}.pdf", cv_bytes
    return None
