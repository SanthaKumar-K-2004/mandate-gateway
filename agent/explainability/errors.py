"""
S02.8 — Decision Trace & Explainability Error Taxonomy.

Domain errors for explainability generation and decision tracing (Section 22, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from enum import Enum


class ExplainabilityErrorCode(str, Enum):
    TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
    INVALID_TRACE_DATA = "INVALID_TRACE_DATA"
    FORMATTING_ERROR = "FORMATTING_ERROR"


class ExplainabilityError(Exception):
    """Base exception for explainability and decision trace operations."""

    def __init__(self, code: ExplainabilityErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
