"""Integration HTTP surface — thin wrappers over interface.py only."""
from __future__ import annotations

from fastapi import APIRouter

from app.integration import interface
from app.integration.interface import AgentCapabilities, HealthStatus, RegistrationResult
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/integration", tags=["integration"])


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    return interface.health_check()


@router.get("/capabilities", response_model=AgentCapabilities)
def capabilities() -> AgentCapabilities:
    return interface.get_capabilities()


@router.post("/events/subscribe", response_model=MessageResponse)
def subscribe_stub() -> MessageResponse:
    return MessageResponse(
        message="Stub accepted — orchestrator event subscription not wired yet."
    )


@router.post("/register", response_model=RegistrationResult)
def register() -> RegistrationResult:
    return interface.register_with_orchestrator()
