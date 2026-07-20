"""Backend entry point.

Start the API server:
    python main.py

Optional CLI (same as `python -m app.cli ...`):
    python main.py cli init-db
    python main.py cli fetch
    python main.py cli run-all
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Dedicated HR Agent ports (avoid common 8000/8080/5173 used by other projects).
DEFAULT_PORT = 8808


def run_server() -> None:
    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", str(DEFAULT_PORT)))
    # Reload can fail with WinError 10013 on some Windows setups; enable via API_RELOAD=1
    reload = os.getenv("API_RELOAD", "0").strip().lower() in {"1", "true", "yes"}

    print(f"Starting HR & Admin Agent API at http://{host}:{port}")
    print(f"Swagger docs: http://{host}:{port}/docs")

    try:
        uvicorn.run(
            "app.api.main:app",
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
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        from app.cli import cli

        sys.argv = [sys.argv[0], *sys.argv[2:]]
        cli()
    else:
        run_server()
