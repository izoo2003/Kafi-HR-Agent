"""Backend entry point.

ASGI servers (Railway, uvicorn CLI) load ``main:app``.
Local ``python main.py`` starts uvicorn with the same app.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Exported for ``uvicorn main:app`` / Railway Nixpacks default.
from app.main import app  # noqa: E402, F401

DEFAULT_PORT = 8808


def run_server() -> None:
    import uvicorn

    # Containers must bind 0.0.0.0; Railway injects PORT.
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT") or os.getenv("API_PORT", str(DEFAULT_PORT)))
    reload = os.getenv("API_RELOAD", "0").strip().lower() in {"1", "true", "yes"}

    print(f"Starting HR & Admin Agent API at http://{host}:{port}")
    print(f"Swagger docs: http://{host}:{port}/docs")

    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=reload,
        )
    except OSError as exc:
        raise SystemExit(
            f"Could not bind {host}:{port} ({exc}). "
            f"Another process is using this port — close it, or change API_PORT / PORT."
        ) from exc


if __name__ == "__main__":
    run_server()
