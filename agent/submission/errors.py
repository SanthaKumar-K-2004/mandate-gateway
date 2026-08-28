"""
S03.4 — Submission Error Taxonomy.

Defines error codes and structured exceptions for submission readiness and system freeze (Section 41, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class SubmissionErrorCode(str, Enum):
    """Enumeration of submission readiness failure modes."""

    REQUIREMENT_NOT_SATISFIED = "REQUIREMENT_NOT_SATISFIED"
    BENCHMARK_EXECUTION_FAILED = "BENCHMARK_EXECUTION_FAILED"
    THREAT_MATRIX_INCOMPLETE = "THREAT_MATRIX_INCOMPLETE"
    SYSTEM_FREEZE_VIOLATION = "SYSTEM_FREEZE_VIOLATION"


class SubmissionError(Exception):
    """Exception raised during submission readiness and system freeze checks."""

    def __init__(
        self,
        code: SubmissionErrorCode,
        message: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.detail = detail
