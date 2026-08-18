"""Auth request/response schemas."""
from __future__ import annotations

import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.common import AuthContext

_USERNAME_RE = re.compile(r"^[a-z0-9._-]+$")


class LoginRequest(BaseModel):
    """Staff: email + password. Self-service: username + PIN. Either identifier works."""

    username: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None
    password: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_identifier(self) -> LoginRequest:
        if not (self.username or self.email):
            raise ValueError("username or email is required")
        return self


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    username: str = Field(min_length=3, max_length=32)
    pin: str = Field(min_length=4, max_length=8)
    department_id: int

    @field_validator("username")
    @classmethod
    def username_format(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not _USERNAME_RE.fullmatch(cleaned):
            raise ValueError(
                "Username may only contain letters, numbers, dots, underscores, and hyphens"
            )
        return cleaned

    @field_validator("pin")
    @classmethod
    def pin_digits(cls, value: str) -> str:
        if not value.isdigit() or not (4 <= len(value) <= 8):
            raise ValueError("PIN must be 4–8 digits")
        return value


class RegisterOptionsDepartment(BaseModel):
    id: int
    name: str


class RegisterOptionsResponse(BaseModel):
    departments: list[RegisterOptionsDepartment]


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    auth: AuthContext


class RefreshRequest(BaseModel):
    refresh_token: str
