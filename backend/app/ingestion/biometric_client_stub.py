"""Biometric device client stub — FEATURE_ATTENDANCE.md §4."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel


class RawPunchRecord(BaseModel):
    device_employee_id: str
    timestamp: datetime
    punch_type: Literal["in", "out"]


class BiometricDeviceClient(Protocol):
    def fetch_punches(self, since: datetime) -> list[RawPunchRecord]:
        """Returns raw check-in/check-out events since a given timestamp."""


class StubBiometricDeviceClient:
    def fetch_punches(self, since: datetime) -> list[RawPunchRecord]:
        _ = since
        return []


_default_client = StubBiometricDeviceClient()


def fetch_punches(since: datetime) -> list[RawPunchRecord]:
    return _default_client.fetch_punches(since)
