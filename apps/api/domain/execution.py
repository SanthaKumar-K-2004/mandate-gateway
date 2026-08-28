"""
S01.11 — Payment Execution Domain Models & Data Types.

Core domain concepts:
  - ExecutionFailureCategory: Safe internal categorization of payment failures.
  - TrustedExecutionRequest: Immutable execution request constructed ONLY by trusted gateway code.
  - ExecutionResult: Normalized domain execution outcome.
  - ExecutionAuditEvidence: Structured audit evidence for append-only ledger tracking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any

from apps.api.domain.types import (
    Currency,
    McpOperation,
    PaymentResultState,
    RejectionReason,
    TransactionState,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@unique
class ExecutionFailureCategory(str, Enum):
    """Safe internal classification of payment execution failures."""

    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    PROVIDER_REJECTED = "PROVIDER_REJECTED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    UNKNOWN_PROVIDER_ERROR = "UNKNOWN_PROVIDER_ERROR"
    INVALID_CONTEXT = "INVALID_CONTEXT"


@dataclass(frozen=True)
class TrustedExecutionRequest:
    """
    Immutable execution request payload.

    MUST be constructed exclusively by trusted Mandate Gateway code after all
    authorization preconditions have passed. NEVER created directly from AI input.
    """

    transaction_id: str
    merchant_id: str
    buyer_id: str
    mandate_id: str
    amount_paise: int
    currency: Currency
    cart_hash: str
    operation: McpOperation
    authorization_reference: str
    idempotency_key: str
    execution_context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    """
    Normalized domain payment execution result.

    Contains zero raw provider credentials, tokens, or sensitive headers.
    """

    success: bool
    transaction_id: str
    state: TransactionState
    external_reference: str | None = None
    failure_code: RejectionReason | None = None
    failure_category: ExecutionFailureCategory | None = None
    safe_message: str = ""
    idempotent_replay: bool = False
    provider_status: PaymentResultState | None = None
    raw_response_redacted: dict[str, Any] | None = None
    executed_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class ExecutionAuditEvidence:
    """
    Safe structured metadata for append-only audit event logging.
    """

    transaction_id: str
    merchant_id: str
    buyer_id: str
    mandate_id: str
    operation: str
    amount_paise: int
    currency: str
    authorization_reference: str
    execution_result_success: bool
    external_reference: str | None
    failure_category: str | None
    provider_status: str | None
    timestamp: datetime = field(default_factory=_utc_now)
