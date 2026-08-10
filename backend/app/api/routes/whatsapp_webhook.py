"""Meta WhatsApp Cloud API webhook — queues PDF/DOCX documents for Sync CVs.

No JWT: Meta verifies via hub.challenge + X-Hub-Signature-256.
FEATURE_CV_SCREENING.md §11.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models.whatsapp import WhatsAppInboundMessage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/whatsapp", tags=["whatsapp"])

DOC_MIME_HINTS = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


def _is_cv_document_payload(doc: dict) -> bool:
    filename = (doc.get("filename") or "").lower()
    mime = (doc.get("mime_type") or "").lower()
    if filename.endswith(".pdf") or filename.endswith(".docx"):
        return True
    if mime in DOC_MIME_HINTS or "pdf" in mime or "wordprocessingml" in mime:
        return True
    return False


@router.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> Response:
    settings = get_settings()
    expected = (settings.whatsapp_verify_token or "").strip()
    if hub_mode == "subscribe" and expected and hub_verify_token == expected and hub_challenge:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict:
    """Always return 200 when possible so Meta does not retry-storm."""
    settings = get_settings()
    body = await request.body()

    app_secret = (settings.whatsapp_app_secret or "").strip()
    if app_secret:
        if not x_hub_signature_256 or not x_hub_signature_256.startswith("sha256="):
            logger.warning("WhatsApp webhook missing signature")
            return {"status": "ignored"}
        expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        provided = x_hub_signature_256.removeprefix("sha256=")
        if not hmac.compare_digest(expected, provided):
            logger.warning("WhatsApp webhook signature mismatch")
            return {"status": "ignored"}

    try:
        import json

        payload = json.loads(body.decode("utf-8") or "{}")
    except Exception:  # noqa: BLE001
        return {"status": "ok"}

    queued = 0
    try:
        for entry in payload.get("entry") or []:
            for change in entry.get("changes") or []:
                value = change.get("value") or {}
                messages = value.get("messages") or []
                for msg in messages:
                    if msg.get("type") != "document":
                        continue
                    doc = msg.get("document") or {}
                    if not _is_cv_document_payload(doc):
                        continue
                    media_id = doc.get("id")
                    wa_id = msg.get("id")
                    if not media_id or not wa_id:
                        continue
                    existing = (
                        db.query(WhatsAppInboundMessage)
                        .filter(WhatsAppInboundMessage.wa_message_id == wa_id)
                        .one_or_none()
                    )
                    if existing:
                        continue
                    ts_raw = msg.get("timestamp")
                    try:
                        received_at = (
                            datetime.fromtimestamp(int(ts_raw), tz=timezone.utc)
                            if ts_raw
                            else datetime.now(timezone.utc)
                        )
                    except (TypeError, ValueError):
                        received_at = datetime.now(timezone.utc)

                    row = WhatsAppInboundMessage(
                        wa_message_id=wa_id,
                        from_phone=msg.get("from"),
                        media_id=media_id,
                        filename=doc.get("filename"),
                        mime_type=doc.get("mime_type"),
                        caption=doc.get("caption"),
                        status="pending",
                        received_at=received_at,
                    )
                    db.add(row)
                    queued += 1
        if queued:
            db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("WhatsApp webhook processing failed")
        db.rollback()

    return {"status": "ok", "queued": queued}
