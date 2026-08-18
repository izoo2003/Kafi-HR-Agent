"""Fetches CV submissions from an Outlook / Microsoft 365 mailbox via
Microsoft Graph — FEATURE_CV_SCREENING.md §11.

Uses application (client-credentials) auth so Railway can sync without an
interactive browser login. Real CVs get category HR-Agent-Processed; non-CV
attachments get HR-Agent-Skipped-NotCV so Sync does not reprocess them.
"""
from __future__ import annotations

import base64
import datetime as dt
import logging
import re
from email.utils import parseaddr
from urllib.parse import quote

from app.core.config import Settings
from app.ingestion.cv_classifier import CV_EXTENSIONS, AttachmentCandidate, pick_cv_attachment
from app.ingestion.cv_submission import CvSubmission, SourceFetchResult

logger = logging.getLogger(__name__)

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
PROCESSED_CATEGORY = "HR-Agent-Processed"
SKIPPED_NOT_CV_CATEGORY = "HR-Agent-Skipped-NotCV"
MAX_MESSAGES_PER_RUN = 20
LOOKBACK_DAYS = 30


def fetch_outlook_submissions(settings: Settings) -> SourceFetchResult:
    """Never raises — returns a SourceFetchResult describing what happened."""
    mailbox = (settings.outlook_mailbox or "").strip()
    tenant = (settings.ms_graph_tenant_id or "").strip()
    client_id = (settings.ms_graph_client_id or "").strip()
    client_secret = (settings.ms_graph_client_secret or "").strip()

    if not all([mailbox, tenant, client_id, client_secret]):
        return SourceFetchResult(
            source="outlook",
            configured=False,
            submissions=[],
            message=(
                "Outlook not configured — set OUTLOOK_MAILBOX, MS_GRAPH_TENANT_ID, "
                "MS_GRAPH_CLIENT_ID, and MS_GRAPH_CLIENT_SECRET (Azure app with Mail.Read)."
            ),
        )

    try:
        import msal  # noqa: F401
        import requests  # noqa: F401
    except ImportError:
        return SourceFetchResult(
            source="outlook",
            configured=False,
            submissions=[],
            message="Outlook sync requires msal + requests — check backend/requirements.txt install.",
        )

    try:
        token = _acquire_token(tenant, client_id, client_secret)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Microsoft Graph auth failed: %s", exc)
        return SourceFetchResult(
            source="outlook",
            configured=False,
            submissions=[],
            message=f"Microsoft Graph authentication failed: {exc}",
        )

    try:
        submissions = _fetch_messages(token, mailbox, settings)
        return SourceFetchResult(source="outlook", configured=True, submissions=submissions)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Outlook / Graph fetch failed")
        return SourceFetchResult(
            source="outlook",
            configured=True,
            submissions=[],
            message=f"Outlook fetch failed: {exc}",
        )


def _acquire_token(tenant: str, client_id: str, client_secret: str) -> str:
    import msal

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant}",
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        err = result.get("error_description") or result.get("error") or str(result)
        raise RuntimeError(err)
    return result["access_token"]


def _graph_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _fetch_messages(token: str, mailbox: str, settings: Settings) -> list[CvSubmission]:
    import requests

    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=LOOKBACK_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    user = quote(mailbox)
    list_url = f"{GRAPH_ROOT}/users/{user}/mailFolders/inbox/messages"
    params: dict[str, str | int] = {
        "$filter": f"hasAttachments eq true and receivedDateTime ge {since}",
        "$orderby": "receivedDateTime desc",
        "$top": MAX_MESSAGES_PER_RUN,
        "$select": "id,subject,from,receivedDateTime,bodyPreview,categories,hasAttachments",
    }

    submissions: list[CvSubmission] = []
    processed = 0
    headers = _graph_headers(token)
    next_url: str | None = list_url
    use_params: dict[str, str | int] | None = params

    while next_url and processed < MAX_MESSAGES_PER_RUN:
        resp = requests.get(next_url, headers=headers, params=use_params, timeout=60)
        use_params = None
        if resp.status_code >= 400:
            raise RuntimeError(f"Graph list messages HTTP {resp.status_code}: {resp.text[:500]}")
        payload = resp.json()
        for msg in payload.get("value", []):
            if processed >= MAX_MESSAGES_PER_RUN:
                break
            processed += 1
            categories = msg.get("categories") or []
            if PROCESSED_CATEGORY in categories or SKIPPED_NOT_CV_CATEGORY in categories:
                continue

            submission, mark_category = _process_message(token, mailbox, msg, settings)
            if submission:
                submissions.append(submission)
            _add_category(token, mailbox, msg["id"], categories, mark_category)

        next_url = payload.get("@odata.nextLink")

    return submissions


def _process_message(
    token: str, mailbox: str, msg: dict, settings: Settings
) -> tuple[CvSubmission | None, str]:
    """Returns (submission_or_None, category_to_apply)."""
    message_id = msg["id"]
    subject = (msg.get("subject") or "").strip()
    from_obj = (msg.get("from") or {}).get("emailAddress") or {}
    sender_name = (from_obj.get("name") or "").strip()
    sender_email = (from_obj.get("address") or "").strip().lower()
    if not sender_name and sender_email:
        sender_name = parseaddr(sender_email)[0] or sender_email.split("@")[0]

    body_text = msg.get("bodyPreview") or ""
    filename, file_bytes = _download_best_cv_attachment(token, mailbox, message_id, settings)
    if file_bytes is None or not filename:
        # No usable attachment — mark processed so we don't keep re-scanning
        return None, PROCESSED_CATEGORY

    return (
        CvSubmission(
            full_name=sender_name or (sender_email.split("@")[0] if sender_email else "Unknown"),
            email=sender_email or None,
            phone=_extract_phone(body_text),
            position_hint=subject or "Unspecified",
            source="outlook",
            source_ref=message_id,
            cv_filename=filename or f"outlook_{message_id[:12]}.pdf",
            cv_bytes=file_bytes,
            submitted_at=_parse_received(msg.get("receivedDateTime")),
            raw_context_text=f"Subject: {subject}\n\n{body_text}",
        ),
        PROCESSED_CATEGORY,
    )


def _download_best_cv_attachment(
    token: str, mailbox: str, message_id: str, settings: Settings
) -> tuple[str | None, bytes | None]:
    import requests

    user = quote(mailbox)
    mid = quote(message_id, safe="")
    url = f"{GRAPH_ROOT}/users/{user}/messages/{mid}/attachments"
    resp = requests.get(url, headers=_graph_headers(token), timeout=60)
    if resp.status_code >= 400:
        logger.warning("Graph attachments HTTP %s: %s", resp.status_code, resp.text[:300])
        return None, None

    candidates: list[AttachmentCandidate] = []
    for att in resp.json().get("value", []):
        if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue
        filename = att.get("name") or ""
        if not filename:
            continue
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in CV_EXTENSIONS:
            continue
        raw = att.get("contentBytes")
        if not raw:
            continue
        file_bytes = base64.b64decode(raw)
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
        is_inline = bool(att.get("isInline"))
        candidates.append(
            AttachmentCandidate(filename=safe_name, content=file_bytes, is_inline=is_inline)
        )
    return pick_cv_attachment(candidates, settings, source="email")


def _add_category(
    token: str, mailbox: str, message_id: str, existing_categories: list, category: str
) -> None:
    import requests

    cats = list(existing_categories or [])
    if category not in cats:
        cats.append(category)
    user = quote(mailbox)
    mid = quote(message_id, safe="")
    url = f"{GRAPH_ROOT}/users/{user}/messages/{mid}"
    try:
        resp = requests.patch(
            url,
            headers=_graph_headers(token),
            json={"categories": cats},
            timeout=30,
        )
        if resp.status_code >= 400:
            logger.warning(
                "Failed to mark Outlook message (%s): %s",
                resp.status_code,
                resp.text[:300],
            )
    except Exception:  # noqa: BLE001
        logger.exception("Failed to mark Outlook message %s", message_id)


def _extract_phone(text: str) -> str | None:
    match = re.search(r"(\+?\d[\d\s\-]{8,14}\d)", text or "")
    return match.group(1).strip() if match else None


def _parse_received(raw: str | None) -> dt.datetime:
    if not raw:
        return dt.datetime.now(dt.timezone.utc)
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return dt.datetime.now(dt.timezone.utc)


def restore_outlook_cv(message_id: str, settings: Settings) -> tuple[str, bytes] | None:
    """Re-download a previously ingested Outlook CV by Graph message id."""
    if not (message_id or "").strip():
        return None
    mailbox = (settings.outlook_mailbox or "").strip()
    tenant = (settings.ms_graph_tenant_id or "").strip()
    client_id = (settings.ms_graph_client_id or "").strip()
    client_secret = (settings.ms_graph_client_secret or "").strip()
    if not all([mailbox, tenant, client_id, client_secret]):
        return None
    try:
        token = _acquire_token(tenant, client_id, client_secret)
        filename, file_bytes = _download_best_cv_attachment(
            token, mailbox, message_id.strip(), settings
        )
    except Exception:
        logger.warning("Outlook CV restore failed for %s", message_id, exc_info=True)
        return None
    if file_bytes and filename:
        return filename, file_bytes
    return None
