"""Placeholder for WhatsApp CV intake (+92 333 0313518).

Not implemented yet — intentionally deferred per project scope. Wired as a
no-op now so the pipeline's ingestion registry already has the seam and
switching it on later (e.g. via WhatsApp Business API / Twilio webhook) is
just filling in `fetch_new_submissions`, no changes needed elsewhere.
"""
from __future__ import annotations

from app.db.models import SourceChannel
from app.ingestion.base import CandidateSubmission, CVIngestor

WHATSAPP_NUMBER = "+92 333 0313518"


class WhatsAppIngestor(CVIngestor):
    source = SourceChannel.WHATSAPP

    def fetch_new_submissions(self) -> list[CandidateSubmission]:
        # TODO: implement via WhatsApp Business API / Twilio webhook once ready.
        return []
