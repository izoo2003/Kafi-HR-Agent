"""Fetches queued WhatsApp document CVs via Meta Cloud API — FEATURE_CV_SCREENING.md §11.

Webhook stores pending rows; Sync downloads media, classifies, and returns
CvSubmission rows for real CVs only.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.ingestion.cv_classifier import classify_cv_document
from app.ingestion.cv_submission import CvSubmission, SourceFetchResult
from app.models.whatsapp import WhatsAppInboundMessage

logger = logging.getLogger(__name__)

MAX_PENDING_PER_RUN = 20


def fetch_whatsapp_submissions(db: Session, settings: Settings) -> SourceFetchResult:
    """Never raises past SourceFetchResult. Mutates pending WhatsAppInboundMessage rows."""
    token = (settings.whatsapp_access_token or "").strip()
    phone_id = (settings.whatsapp_phone_number_id or "").strip()
    if not token or not phone_id:
        return SourceFetchResult(
            source="whatsapp",
            configured=False,
            submissions=[],
            message=(
                "WhatsApp not configured — set WHATSAPP_ACCESS_TOKEN and "
                "WHATSAPP_PHONE_NUMBER_ID (Meta Cloud API)."
            ),
        )

    try:
        import requests  # noqa: F401
    except ImportError:
        return SourceFetchResult(
            source="whatsapp",
            configured=False,
            submissions=[],
            message="WhatsApp sync requires requests — check backend/requirements.txt install.",
        )

    pending = (
        db.query(WhatsAppInboundMessage)
        .filter(WhatsAppInboundMessage.status == "pending")
        .order_by(WhatsAppInboundMessage.received_at.asc())
        .limit(MAX_PENDING_PER_RUN)
        .all()
    )

    submissions: list[CvSubmission] = []
    try:
        for row in pending:
            try:
                filename, content = _download_media(settings, row.media_id, row.filename)
            except Exception as exc:  # noqa: BLE001
                logger.warning("WhatsApp media download failed for %s: %s", row.wa_message_id, exc)
                row.status = "failed"
                row.skip_reason = f"download failed: {exc}"
                continue

            caption = (row.caption or "").strip()
            source_hint = "form" if re.search(r"cv|resume|curriculum", caption, re.I) else "whatsapp"
            classification = classify_cv_document(
                filename=filename, content=content, settings=settings, source=source_hint
            )
            if not classification.is_cv:
                row.status = "skipped"
                row.skip_reason = classification.reason
                continue

            phone = (row.from_phone or "").strip()
            if phone and not phone.startswith("+"):
                phone = f"+{phone}"

            submissions.append(
                CvSubmission(
                    full_name=_display_name_from_phone(phone),
                    email=None,
                    phone=phone or None,
                    position_hint=(row.caption or "").strip() or "Unspecified",
                    source="whatsapp",
                    source_ref=row.wa_message_id,
                    cv_filename=filename,
                    cv_bytes=content,
                    submitted_at=row.received_at,
                    raw_context_text=row.caption,
                )
            )
            row.status = "imported"
            row.skip_reason = None

        db.flush()
        return SourceFetchResult(source="whatsapp", configured=True, submissions=submissions)
    except Exception as exc:  # noqa: BLE001
        logger.exception("WhatsApp fetch failed")
        return SourceFetchResult(
            source="whatsapp",
            configured=True,
            submissions=[],
            message=f"WhatsApp fetch failed: {exc}",
        )


def _download_media(
    settings: Settings, media_id: str, preferred_filename: str | None
) -> tuple[str, bytes]:
    import requests

    version = (settings.whatsapp_api_version or "v21.0").strip()
    token = settings.whatsapp_access_token.strip()
    headers = {"Authorization": f"Bearer {token}"}

    meta_url = f"https://graph.facebook.com/{version}/{media_id}"
    meta_resp = requests.get(meta_url, headers=headers, timeout=60)
    if meta_resp.status_code >= 400:
        raise RuntimeError(f"media metadata HTTP {meta_resp.status_code}: {meta_resp.text[:300]}")
    meta = meta_resp.json()
    download_url = meta.get("url")
    if not download_url:
        raise RuntimeError("media metadata missing url")

    file_resp = requests.get(download_url, headers=headers, timeout=120)
    if file_resp.status_code >= 400:
        raise RuntimeError(f"media download HTTP {file_resp.status_code}")

    mime = (meta.get("mime_type") or "").lower()
    filename = preferred_filename or meta.get("filename") or f"whatsapp_{media_id}"
    suffix = Path(filename).suffix.lower()
    if not suffix:
        if "pdf" in mime:
            filename = f"{filename}.pdf"
        elif "wordprocessingml" in mime or "msword" in mime:
            filename = f"{filename}.docx"
        elif mime.startswith("image/"):
            ext = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
                "image/heic": ".heic",
                "image/heif": ".heif",
            }.get(mime, ".jpg")
            filename = f"{filename}{ext}"
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return safe, file_resp.content


def restore_whatsapp_cv(wa_message_id: str, settings: Settings) -> tuple[str, bytes] | None:
    """Re-download WhatsApp media if Meta still has the file (media ids expire)."""
    ref = (wa_message_id or "").strip()
    token = (settings.whatsapp_access_token or "").strip()
    if not ref or not token:
        return None
    try:
        from app.core.db import get_session_factory

        SessionLocal = get_session_factory()
        with SessionLocal() as db:
            row = (
                db.query(WhatsAppInboundMessage)
                .filter(WhatsAppInboundMessage.wa_message_id == ref)
                .one_or_none()
            )
            if row is None or not (row.media_id or "").strip():
                return None
            return _download_media(settings, row.media_id, row.filename)
    except Exception:
        logger.warning("WhatsApp CV restore failed for %s", ref, exc_info=True)
        return None


def _display_name_from_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return f"WhatsApp {digits[-4:]}" if digits else "WhatsApp applicant"
