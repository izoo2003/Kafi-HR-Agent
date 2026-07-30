"""Backend entry point — uvicorn serves app.main:app."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

DEFAULT_PORT = 8808


def run_server() -> None:
    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", str(DEFAULT_PORT)))
    reload = os.getenv("API_RELOAD", "0").strip().lower() in {"1", "true", "yes"}

    print(f"Starting HR & Admin Agent API at http://{host}:{port}")
    print(f"Swagger docs: http://{host}:{port}/docs")

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
        )
    except OSError as exc:
        raise SystemExit(
            f"Could not bind {host}:{port} ({exc}). "
            f"Another process is using this port — close it, or change API_PORT in backend/.env."
        ) from exc


if __name__ == "__main__":
    run_server()
