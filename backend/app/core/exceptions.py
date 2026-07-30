"""Domain exception hierarchy — maps to API_ENDPOINTS.md §11 error codes."""
from __future__ import annotations

from typing import Any


class HrAdminAgentError(Exception):
    """Base class for all interface-boundary / domain errors."""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotOwnedByThisAgent(HrAdminAgentError):
    code = "business_rule_violation"
    http_status = 400
    expected_agent_key: str = "utilities_maintenance"

    def __init__(
        self,
        message: str = "This domain is owned by a sibling agent.",
        *,
        expected_agent_key: str = "utilities_maintenance",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details={**(details or {}), "expected_agent_key": expected_agent_key})
        self.expected_agent_key = expected_agent_key


class PermissionDenied(HrAdminAgentError):
    code = "forbidden"
    http_status = 403


class EntityNotFound(HrAdminAgentError):
    code = "not_found"
    http_status = 404


class InvalidAuthContext(HrAdminAgentError):
    code = "unauthorized"
    http_status = 401


class ValidationFailed(HrAdminAgentError):
    code = "validation_error"
    http_status = 422


class ConflictError(HrAdminAgentError):
    code = "conflict"
    http_status = 409


class BusinessRuleViolation(HrAdminAgentError):
    code = "business_rule_violation"
    http_status = 400
