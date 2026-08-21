"""Cloudflare Workers AI text-to-image client."""
from __future__ import annotations

import base64
import logging
from typing import Any

import requests

from app.core.config import Settings
from app.core.exceptions import BusinessRuleViolation

logger = logging.getLogger(__name__)


def cloudflare_image_configured(settings: Settings) -> bool:
    return bool(
        (settings.cloudflare_account_id or "").strip()
        and (settings.cloudflare_api_token or "").strip()
    )


def generate_image_bytes(
    *,
    prompt: str,
    settings: Settings,
    steps: int | None = None,
) -> bytes:
    """Call Workers AI image model; returns JPEG/PNG bytes."""
    account_id = (settings.cloudflare_account_id or "").strip()
    token = (settings.cloudflare_api_token or "").strip()
    if not account_id or not token:
        raise BusinessRuleViolation(
            "Cloudflare image generation is not configured. Set CLOUDFLARE_ACCOUNT_ID "
            "and CLOUDFLARE_API_TOKEN (e.g. on Railway)."
        )

    model = (settings.cloudflare_image_model or "@cf/black-forest-labs/flux-1-schnell").strip()
    model_path = model if model.startswith("@cf/") else f"@cf/{model.lstrip('/')}"
    step_count = int(steps if steps is not None else settings.cloudflare_image_steps or 4)
    step_count = max(1, min(step_count, 8))
    timeout = max(30, int(settings.cloudflare_image_timeout or 120))

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/{model_path}"
    )
    payload: dict[str, Any] = {
        "prompt": prompt[:2048],
        "steps": step_count,
    }

    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.exception("Cloudflare Workers AI request failed")
        raise BusinessRuleViolation(
            f"Cloudflare image generation request failed: {exc}"
        ) from exc

    if resp.status_code >= 400:
        detail = (resp.text or "")[:400]
        logger.error("Cloudflare AI HTTP %s: %s", resp.status_code, detail)
        raise BusinessRuleViolation(
            f"Cloudflare image generation failed (HTTP {resp.status_code}). "
            "Check CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, and Workers AI access."
        )

    content_type = (resp.headers.get("Content-Type") or "").lower()
    if "application/json" in content_type or resp.content[:1] == b"{":
        try:
            data = resp.json()
        except ValueError as exc:
            raise BusinessRuleViolation(
                "Cloudflare returned an unreadable image response"
            ) from exc
        if isinstance(data, dict) and data.get("success") is False:
            errors = data.get("errors") or data.get("messages") or data
            raise BusinessRuleViolation(f"Cloudflare image generation error: {errors}")
        image_b64 = None
        if isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, dict):
                image_b64 = result.get("image")
            if not image_b64:
                image_b64 = data.get("image")
        if not image_b64 or not isinstance(image_b64, str):
            raise BusinessRuleViolation(
                "Cloudflare image response did not include image data"
            )
        try:
            return base64.b64decode(image_b64)
        except Exception as exc:
            raise BusinessRuleViolation(
                "Cloudflare image data could not be decoded"
            ) from exc

    # Some gateways return raw binary image bytes
    if resp.content:
        return resp.content
    raise BusinessRuleViolation("Cloudflare returned an empty image")
