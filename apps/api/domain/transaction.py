"""
S01.15 / S01.1 — Transaction Data Contract.

Transaction record contract tracking an AI commerce action (Section 26, PROJECT_CONTEXT.md).

Core binding:
    transaction_id + cart_hash + mandate_id + policy_version

Data contract only — state machine transitions belong to S01.11 (transaction_engine.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

from apps.api.domain.types import (
    Currency,
    RejectionReason,
    TransactionState,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Transaction(BaseModel):
    """
    A transaction record contract tracking the full lifecycle of an AI commerce action.

    Immutable contract (frozen=True).
    """

    model_config = {"frozen": True}

    transaction_id: str = Field(default_factory=_new_uuid)

    buyer_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    mandate_version: int = Field(..., ge=1)
    policy_version: int = Field(..., ge=1)

    cart_id: str | None = Field(default=None)
    cart_hash: str | None = Field(
        default=None,
        description="SHA-256 hex digest of the approved cart.",
    )

    amount_paise: int = Field(default=0, ge=0)
    currency: Currency = Field(default=Currency.INR)

    state: TransactionState = Field(default=TransactionState.DRAFT)

    rejection_reason: RejectionReason | None = Field(default=None)
    rejection_detail: str | None = Field(default=None)

    idempotency_key: str = Field(
        default_factory=_new_uuid,
        description="Unique key preventing duplicate execution.",
    )
    nonce: str | None = Field(
        default=None,
        description="Single-use execution nonce.",
    )

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    step_up_required_at: datetime | None = Field(default=None)
    step_up_approved_at: datetime | None = Field(default=None)
    step_up_amount_paise: int | None = Field(default=None)

    razorpay_order_id: str | None = Field(default=None)
    razorpay_payment_id: str | None = Field(default=None)

    @model_validator(mode="after")
    def _validate_rejection_consistency(self) -> Transaction:
        if self.state is TransactionState.REJECTED and self.rejection_reason is None:
            raise ValueError("Rejected transaction must have a rejection_reason.")
        if self.state is not TransactionState.REJECTED and self.rejection_reason is not None:
            raise ValueError(
                f"rejection_reason set but state is {self.state.value!r}, not REJECTED."
            )
        return self

    def is_executable(self) -> bool:
        """Return True only if transaction is in AUTHORIZED state."""
        return self.state.can_execute()

    def is_terminal(self) -> bool:
        """Return True if no further state transitions are possible."""
        return self.state.is_terminal()


class TransactionStateError(ValueError):
    """Raised when an illegal transaction state transition is attempted."""
