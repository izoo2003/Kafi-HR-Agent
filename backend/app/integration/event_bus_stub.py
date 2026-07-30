"""Abstracted event publish — local only today; swap transport later without touching callers."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def publish_event(event_name: str, payload: dict[str, Any]) -> None:
    """Today: log locally. Later: shared bus (Kafka/Redis/webhook — TBD by orchestrator)."""
    logger.info("event_bus.publish name=%s payload_keys=%s", event_name, list(payload.keys()))
