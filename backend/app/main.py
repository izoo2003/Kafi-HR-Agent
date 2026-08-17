"""FastAPI application — startup sequence per BACKEND_ARCHITECTURE.md §7."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.db import Base, get_engine, get_session_factory
from app.core.exceptions import HrAdminAgentError
from app.integration import interface
import app.models  # noqa: F401 — register metadata

logger = logging.getLogger(__name__)


def _error_payload(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def _restore_google_oauth_token(settings) -> None:
    """Ephemeral filesystems (Railway) lose credentials/*.json on redeploy. If a token was
    minted once locally and pasted into GOOGLE_OAUTH_TOKEN_JSON, write it back so Gmail/Google
    Form sync keeps working without a fresh interactive OAuth consent every deploy."""
    if not settings.google_oauth_token_json:
        return
    token_path = settings.resolved_path(settings.google_oauth_token_file)
    if token_path.exists():
        return
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(settings.google_oauth_token_json, encoding="utf-8")
    print(f"[startup] Restored Google OAuth token to {token_path}", flush=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.uploads_cvs_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_employees_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.cv_files_dir.mkdir(parents=True, exist_ok=True)
    settings.credentials_dir.mkdir(parents=True, exist_ok=True)
    _restore_google_oauth_token(settings)

    try:
        from app.core import supabase_storage

        if supabase_storage.storage_configured(settings):
            bucket = supabase_storage.ensure_employee_documents_bucket(settings)
            print(f"[startup] Supabase Storage ready (bucket={bucket})", flush=True)
        else:
            print(
                "[startup] Supabase Storage not configured — employee files stay on local disk",
                flush=True,
            )
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] Supabase Storage setup skipped: {exc}", flush=True)

    db_kind = "Supabase Postgres" if settings.database_url.startswith("postgresql") else "SQLite"
    print(f"[startup] Connecting to {db_kind}…", flush=True)
    engine = get_engine()

    print("[startup] Ensuring tables exist (first cloud boot can take ~30–60s)…", flush=True)
    Base.metadata.create_all(bind=engine)

    print("[startup] Running seeds…", flush=True)
    SessionLocal = get_session_factory()
    with SessionLocal() as db:
        from app.services.seed_service import run_all_seeds

        run_all_seeds(db)

    result = interface.register_with_orchestrator()
    logger.info("Orchestrator registration: %s — %s", result.status, result.message)

    from app.services.kpi_scheduler import start_kpi_reminder_scheduler, stop_kpi_reminder_scheduler

    start_kpi_reminder_scheduler()
    print("[startup] Ready.", flush=True)

    yield

    stop_kpi_reminder_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HR & Admin Agent",
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HrAdminAgentError)
    async def handle_domain_error(_request: Request, exc: HrAdminAgentError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_payload(exc.code, exc.message, exc.details or None),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else None
        message = "Request validation failed"
        if first and isinstance(first.get("msg"), str):
            loc = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
            msg = first["msg"].removeprefix("Value error, ").strip()
            message = f"{loc}: {msg}" if loc else msg
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                "validation_error",
                message,
                {"errors": errors},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload("internal_error", "An unexpected error occurred"),
        )

    app.include_router(api_router)

    @app.get("/health")
    def root_health() -> dict:
        status = interface.health_check()
        return status.model_dump()

    return app


app = create_app()
