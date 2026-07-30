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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.uploads_cvs_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

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
    print("[startup] Ready.", flush=True)

    yield


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
