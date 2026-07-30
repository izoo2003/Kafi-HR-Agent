"""FastAPI app for the HR & Admin agent's CV Ranking module.

Run with: uvicorn app.api.main:app --reload (from the backend/ directory).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import pipeline, positions, reports
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="HR & Admin Agent API",
    description="CV Ranking capability — ingestion, scoring, ranking, reporting.",
    version="0.1.0",
    lifespan=lifespan,
)

# Vite proxy is preferred; these origins are a fallback for direct API calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5288",
        "http://127.0.0.1:5288",
        "http://[::1]:5288",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "agent": "hr_admin_agent"}


app.include_router(positions.router)
app.include_router(pipeline.router)
app.include_router(reports.router)
