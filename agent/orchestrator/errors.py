"""
S03.2 — End-to-End Orchestrator Domain Error Taxonomy.

Defines error codes and structured exceptions for full end-to-end commerce orchestration (Section 24, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class OrchestratorErrorCode(str, Enum):
    """Enumeration of end-to-end orchestration failure modes."""

    INTENT_NORMALIZATION_FAILED = "INTENT_NORMALIZATION_FAILED"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    MANDATE_EVALUATION_FAILED = "MANDATE_EVALUATION_FAILED"
    POLICY_EVALUATION_FAILED = "POLICY_EVALUATION_FAILED"
    CART_INTEGRITY_FAILED = "CART_INTEGRITY_FAILED"
    BUDGET_RESERVATION_FAILED = "BUDGET_RESERVATION_FAILED"
    REPLAY_CHECK_FAILED = "REPLAY_CHECK_FAILED"
    NONCE_VALIDATION_FAILED = "NONCE_VALIDATION_FAILED"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    AUDIT_LOGGING_FAILED = "AUDIT_LOGGING_FAILED"
    RECEIPT_SIGNING_FAILED = "RECEIPT_SIGNING_FAILED"
    SYSTEM_INTERNAL_ERROR = "SYSTEM_INTERNAL_ERROR"


class OrchestratorError(Exception):
    """Exception raised for errors during end-to-end commerce orchestration."""

    def __init__(
        self,
        code: OrchestratorErrorCode,
        message: str,
        detail: str | None = None,
    ) -> None:
        super().__init__(f"[{code.value}] {message}")
        self.code = code
        self.message = message
        self.detail = detail
