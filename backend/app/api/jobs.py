"""In-memory pipeline job status for the dashboard.

Keeps long Gmail/Gemini work off the HTTP request so the UI does not sit
on a single blocked fetch for many minutes (and so /health stays responsive).
"""
from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

_lock = threading.Lock()


@dataclass
class JobState:
    status: str = "idle"  # idle | running | succeeded | failed
    action: str = ""
    message: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


_state = JobState()


def get_job_state() -> dict[str, Any]:
    with _lock:
        return asdict(_state)


def _set(**kwargs: Any) -> None:
    with _lock:
        for key, value in kwargs.items():
            setattr(_state, key, value)


def try_start_job(action: str, worker: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Starts a background job if none is running. Returns current state."""
    with _lock:
        if _state.status == "running":
            return asdict(_state)
        _state.status = "running"
        _state.action = action
        _state.message = f"{action} started…"
        _state.result = {}
        _state.error = None
        _state.started_at = datetime.now(timezone.utc).isoformat()
        _state.finished_at = None

    def _run() -> None:
        try:
            result = worker()
            _set(
                status="succeeded",
                message=f"{action} finished.",
                result=result,
                finished_at=datetime.now(timezone.utc).isoformat(),
            )
        except Exception as exc:
            logger.exception("Pipeline job %s failed", action)
            _set(
                status="failed",
                message=f"{action} failed.",
                error=str(exc),
                finished_at=datetime.now(timezone.utc).isoformat(),
            )

    threading.Thread(target=_run, daemon=True, name=f"pipeline-{action}").start()
    return get_job_state()
