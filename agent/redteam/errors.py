"""
S02.7 — Red-Team Chaos Lab & Adversarial Security Error Definitions.

Defines structured exception types and error codes for red-team attack simulation
and fail-closed security assertions.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class RedTeamErrorCode(str, Enum):
    """Machine-readable error codes for red-team attack simulation."""

    UNKNOWN_ATTACK_TYPE = "UNKNOWN_ATTACK_TYPE"
    ATTACK_EXPLOITED = "ATTACK_EXPLOITED"
    SIMULATION_SETUP_FAILED = "SIMULATION_SETUP_FAILED"
    DECISION_TRACE_UNAVAILABLE = "DECISION_TRACE_UNAVAILABLE"


class RedTeamError(Exception):
    """Base exception for red-team attack simulation operations."""

    def __init__(
        self,
        code: RedTeamErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


class RedTeamExploitedError(RedTeamError):
    """Raised when an attack scenario unexpectedly succeeds (security boundary bypass)."""

    def __init__(
        self,
        attack_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = {"attack_type": attack_type, **(details or {})}
        super().__init__(
            code=RedTeamErrorCode.ATTACK_EXPLOITED,
            message=message,
            details=merged_details,
        )
