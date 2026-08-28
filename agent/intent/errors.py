"""
S02.3 — Intent Normalization Error Codes & Exceptions.

Defines domain exceptions and structured error codes for AI intent validation,
prompt injection defense, catalog poisoning scanning, and arithmetic verification.
"""

from __future__ import annotations

from enum import Enum


class IntentErrorCode(str, Enum):
    """Structured machine-readable error codes for intent validation failures."""

    MALFORMED_INTENT_PAYLOAD = "MALFORMED_INTENT_PAYLOAD"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    CATALOG_POISONING_DETECTED = "CATALOG_POISONING_DETECTED"
    INVALID_LINE_ITEM_MATH = "INVALID_LINE_ITEM_MATH"
    AUTHORITY_INJECTION_ATTEMPT = "AUTHORITY_INJECTION_ATTEMPT"
    UNAUTHORIZED_CURRENCY = "UNAUTHORIZED_CURRENCY"
    MISSING_MANDATORY_FIELD = "MISSING_MANDATORY_FIELD"
    INTENT_SIZE_EXCEEDED = "INTENT_SIZE_EXCEEDED"
    INTENT_PROCESSING_FAILED = "INTENT_PROCESSING_FAILED"


class IntentValidationError(Exception):
    """Domain error raised during intent parsing, sanitization, or math verification."""

    def __init__(self, code: IntentErrorCode, detail: str) -> None:
        super().__init__(f"[{code.value}] {detail}")
        self.code: IntentErrorCode = code
        self.detail: str = detail
