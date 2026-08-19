"""Re-fetch a missing CV from its original source and persist it to Storage."""
from __future__ import annotations

import logging
import re

from app.core.config import get_settings
from app.models.cv_screening import Candidate

logger = logging.getLogger(__name__)


def restore_missing_cv(candidate: Candidate) -> tuple[str, bytes] | None:
    """Returns (filename, bytes) if the original source still has the file."""
    settings = get_settings()
    source = (candidate.source or "").strip().lower()
    ref = (candidate.source_ref or "").strip()
    if not ref:
        return None

    try:
        if source in {"gmail"}:
            from app.ingestion.gmail_ingestor import restore_gmail_cv

            return restore_gmail_cv(ref, settings)
        if source in {"google_form", "form"}:
            from app.ingestion.google_form_ingestor import restore_form_cv

            return restore_form_cv(ref, settings)
        if source in {"outlook"}:
            from app.ingestion.outlook_ingestor import restore_outlook_cv

            return restore_outlook_cv(ref, settings)
        if source in {"webmail", "imap", "email"}:
            from app.ingestion.imap_ingestor import restore_imap_cv

            return restore_imap_cv(ref, settings)
        if source in {"whatsapp"}:
            from app.ingestion.whatsapp_ingestor import restore_whatsapp_cv

            return restore_whatsapp_cv(ref, settings)

        # Source blank or unexpected — infer from the source_ref shape.
        if re.fullmatch(r"form_row_\d+", ref):
            from app.ingestion.google_form_ingestor import restore_form_cv

            return restore_form_cv(ref, settings)
        if ref.startswith("<") or re.search(r"@.+>", ref) or ref.lower().startswith("imap-uid-"):
            from app.ingestion.imap_ingestor import restore_imap_cv

            found = restore_imap_cv(ref, settings)
            if found:
                return found
        from app.ingestion.gmail_ingestor import restore_gmail_cv

        found = restore_gmail_cv(ref, settings)
        if found:
            return found
        from app.ingestion.imap_ingestor import restore_imap_cv

        return restore_imap_cv(ref, settings)
    except Exception:
        logger.warning(
            "CV restore failed for candidate %s source=%s",
            candidate.id,
            source,
            exc_info=True,
        )
        return None
