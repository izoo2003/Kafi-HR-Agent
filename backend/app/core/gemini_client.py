"""Shared Gemini helpers — API key rotation + model fallbacks."""
from __future__ import annotations

import logging
import re
import threading
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Free-tier daily quotas typically reset at midnight Pacific Time.
try:
    _PACIFIC = ZoneInfo("America/Los_Angeles")
except Exception:  # noqa: BLE001 — Windows without tzdata
    _PACIFIC = UTC

_lock = threading.Lock()
# pool_id -> preferred key index
_preferred_index: dict[str, int] = {}
# (pool_id, key_fingerprint) -> exhausted_until (UTC) — whole key burned
_exhausted_until: dict[tuple[str, str], datetime] = {}
# (pool_id, key_fingerprint, model) -> exhausted_until (UTC) — single model burned
_model_exhausted_until: dict[tuple[str, str, str], datetime] = {}


class GeminiQuotaExhausted(RuntimeError):
    """Raised when every key in a pool is rate-limited / quota-exhausted."""

    def __init__(self, message: str, *, reset_at: datetime | None = None):
        super().__init__(message)
        self.reset_at = reset_at


def parse_model_chain(primary: str, fallbacks_csv: str = "") -> list[str]:
    """Build ordered unique model list: primary first, then fallbacks."""
    models: list[str] = []
    for raw in [primary, *fallbacks_csv.split(",")]:
        name = (raw or "").strip()
        if name and name not in models:
            models.append(name)
    return models


def _normalize_keys(keys: list[str] | str | None) -> list[str]:
    if keys is None:
        return []
    if isinstance(keys, str):
        keys = [keys]
    out: list[str] = []
    for raw in keys:
        key = (raw or "").strip()
        if not key or key.startswith("your_"):
            continue
        if key not in out:
            out.append(key)
    return out


def _fingerprint(key: str) -> str:
    return key[-12:] if len(key) >= 12 else key


def _is_quota_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    markers = (
        "429",
        "resource_exhausted",
        "resource exhausted",
        "quota",
        "rate limit",
        "ratelimit",
        "too many requests",
        "exceeded your current quota",
        "generate_requests_per_day",
        "generate_content_free_tier",
        "limit: 0",
    )
    return any(m in text for m in markers)


def _parse_retry_delay(exc: BaseException) -> timedelta | None:
    text = str(exc)
    # "Please retry in 42.5s" / "retry in 123 seconds"
    m = re.search(r"retry in\s+(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds)?", text, re.I)
    if m:
        return timedelta(seconds=float(m.group(1)))
    # RetryInfo { retry_delay { seconds: 60 } }
    m = re.search(r"retry_delay\s*\{[^}]*seconds:\s*(\d+)", text, re.I)
    if m:
        return timedelta(seconds=int(m.group(1)))
    m = re.search(r"Retry-After[=:\s]+(\d+)", text, re.I)
    if m:
        return timedelta(seconds=int(m.group(1)))
    return None


def _default_daily_reset_utc(now: datetime | None = None) -> datetime:
    """Next midnight America/Los_Angeles, as UTC."""
    now_utc = now or datetime.now(UTC)
    now_pt = now_utc.astimezone(_PACIFIC)
    next_midnight_pt = (now_pt + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    if now_pt.hour == 0 and now_pt.minute == 0 and now_pt.second < 5:
        # Already at midnight — treat as "now" briefly
        return now_utc
    return next_midnight_pt.astimezone(UTC)


def _format_reset_time(reset_at: datetime) -> str:
    local = reset_at.astimezone()
    pt = reset_at.astimezone(_PACIFIC)
    return (
        f"{local.strftime('%Y-%m-%d %H:%M:%S %Z')} "
        f"(Pacific: {pt.strftime('%Y-%m-%d %H:%M:%S %Z')})"
    )


def _quota_until(exc: BaseException, now: datetime) -> datetime:
    delay = _parse_retry_delay(exc) or (_default_daily_reset_utc(now) - now)
    until = now + delay
    if until <= now:
        until = _default_daily_reset_utc(now)
    return until


def _mark_exhausted(pool_id: str, key: str, until: datetime) -> None:
    with _lock:
        _exhausted_until[(pool_id, _fingerprint(key))] = until


def _mark_model_exhausted(
    pool_id: str, key: str, model_name: str, until: datetime
) -> None:
    with _lock:
        _model_exhausted_until[(pool_id, _fingerprint(key), model_name)] = until


def _is_exhausted(pool_id: str, key: str, now: datetime) -> bool:
    with _lock:
        until = _exhausted_until.get((pool_id, _fingerprint(key)))
    if until is None:
        return False
    if now >= until:
        with _lock:
            _exhausted_until.pop((pool_id, _fingerprint(key)), None)
        return False
    return True


def _is_model_exhausted(
    pool_id: str, key: str, model_name: str, now: datetime
) -> bool:
    with _lock:
        until = _model_exhausted_until.get(
            (pool_id, _fingerprint(key), model_name)
        )
    if until is None:
        return False
    if now >= until:
        with _lock:
            _model_exhausted_until.pop(
                (pool_id, _fingerprint(key), model_name), None
            )
        return False
    return True


def _ordered_keys(pool_id: str, keys: list[str]) -> list[str]:
    """Rotate starting from preferred index: key A → B → back to A."""
    if not keys:
        return []
    with _lock:
        start = _preferred_index.get(pool_id, 0) % len(keys)
    return [keys[(start + i) % len(keys)] for i in range(len(keys))]


def _remember_success(pool_id: str, keys: list[str], key: str) -> None:
    try:
        idx = keys.index(key)
    except ValueError:
        return
    with _lock:
        _preferred_index[pool_id] = idx


def _soonest_reset(pool_id: str, keys: list[str], now: datetime) -> datetime:
    resets: list[datetime] = []
    fps = {_fingerprint(k) for k in keys}
    with _lock:
        for key in keys:
            until = _exhausted_until.get((pool_id, _fingerprint(key)))
            if until is not None and until > now:
                resets.append(until)
        for (pid, fp, _model), until in _model_exhausted_until.items():
            if pid == pool_id and fp in fps and until > now:
                resets.append(until)
    return min(resets) if resets else _default_daily_reset_utc(now)


def generate_content_with_fallback(
    *,
    api_key: str | list[str] | None = None,
    api_keys: list[str] | None = None,
    models: list[str],
    prompt: str | list[Any],
    pool_id: str = "default",
) -> Any:
    """Call Gemini with key rotation and per-model fallbacks.

    Order for each key: try primary model, then each fallback model.
    A quota hit on one model only skips that model — the next fallback is tried
    on the same key. The whole key is marked exhausted only after every model
    in the chain hits quota. Then the next key is tried the same way.
    """
    keys = _normalize_keys(api_keys if api_keys is not None else api_key)
    if not keys:
        raise RuntimeError("Gemini API key is not configured")
    if not models:
        raise RuntimeError("No Gemini models configured")

    import google.generativeai as genai

    now = datetime.now(UTC)
    ordered = _ordered_keys(pool_id, keys)
    last_exc: Exception | None = None
    keys_fully_exhausted = 0

    for key in ordered:
        if _is_exhausted(pool_id, key, now):
            keys_fully_exhausted += 1
            logger.info(
                "Skipping exhausted Gemini key …%s in pool %s",
                _fingerprint(key),
                pool_id,
            )
            continue

        genai.configure(api_key=key)
        model_quota_hits = 0
        for model_name in models:
            if _is_model_exhausted(pool_id, key, model_name, now):
                model_quota_hits += 1
                logger.info(
                    "Skipping exhausted Gemini model %s on key …%s (pool %s)",
                    model_name,
                    _fingerprint(key),
                    pool_id,
                )
                continue
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                _remember_success(pool_id, keys, key)
                return response
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if _is_quota_error(exc):
                    until = _quota_until(exc, now)
                    _mark_model_exhausted(pool_id, key, model_name, until)
                    model_quota_hits += 1
                    logger.warning(
                        "Gemini model %s exhausted on key …%s until %s; "
                        "trying next fallback model: %s",
                        model_name,
                        _fingerprint(key),
                        until.isoformat(),
                        exc,
                    )
                    continue
                logger.warning(
                    "Gemini model %s failed on key …%s: %s",
                    model_name,
                    _fingerprint(key),
                    exc,
                )

        # All models on this key hit quota → mark key exhausted, prefer next key
        if model_quota_hits >= len(models):
            until = _soonest_reset(pool_id, [key], now)
            _mark_exhausted(pool_id, key, until)
            keys_fully_exhausted += 1
            with _lock:
                try:
                    cur = keys.index(key)
                    _preferred_index[pool_id] = (cur + 1) % len(keys)
                except ValueError:
                    pass
            logger.warning(
                "All models exhausted for Gemini key …%s in pool %s; rotating key",
                _fingerprint(key),
                pool_id,
            )

    now = datetime.now(UTC)
    all_exhausted = all(_is_exhausted(pool_id, key, now) for key in keys)
    if all_exhausted or (
        keys_fully_exhausted >= len(keys) and last_exc and _is_quota_error(last_exc)
    ):
        reset_at = _soonest_reset(pool_id, keys, now)
        when = _format_reset_time(reset_at)
        raise GeminiQuotaExhausted(
            "All free API keys have been exhausted. "
            f"Wait until {when} to do more work.",
            reset_at=reset_at,
        )

    raise RuntimeError(
        f"All Gemini keys/models failed for pool {pool_id}: {last_exc}"
    ) from last_exc
