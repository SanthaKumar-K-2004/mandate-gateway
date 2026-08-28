"""
[S01.11 — Gateway Execution Boundary & Transaction Engine]

State machine transition evaluation engine for Transaction (Section 26, PROJECT_CONTEXT.md).

Forbidden transitions (enforced deterministically):
    REJECTED    → EXECUTING
    EXPIRED     → EXECUTING
    CONSUMED    → EXECUTING
    COMPLETED   → EXECUTING
    ROLLED_BACK → COMMITTED
"""

from __future__ import annotations

from datetime import datetime, timezone

from apps.api.domain.transaction import Transaction, TransactionStateError
from apps.api.domain.types import (
    RejectionReason,
    TransactionState,
    _TRANSACTION_LEGAL_TRANSITIONS,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def transition_transaction(
    transaction: Transaction,
    new_state: TransactionState,
    *,
    rejection_reason: RejectionReason | None = None,
    rejection_detail: str | None = None,
    cart_id: str | None = None,
    cart_hash: str | None = None,
    amount_paise: int | None = None,
    nonce: str | None = None,
    razorpay_order_id: str | None = None,
    razorpay_payment_id: str | None = None,
    step_up_amount_paise: int | None = None,
) -> Transaction:
    """
    Advance *transaction* to *new_state*.

    Returns a new Transaction with the updated state and timestamp.
    Raises TransactionStateError if the transition is illegal.
    """
    legal = _TRANSACTION_LEGAL_TRANSITIONS.get(transaction.state, frozenset())
    if new_state not in legal:
        raise TransactionStateError(
            f"Illegal transaction transition: "
            f"{transaction.state.value} → {new_state.value}. "
            f"Legal next states: {sorted(s.value for s in legal)}"
        )

    # Enforce rejection invariant
    if new_state is TransactionState.REJECTED and rejection_reason is None:
        raise ValueError("Must provide rejection_reason when transitioning to REJECTED.")
    if new_state is not TransactionState.REJECTED and rejection_reason is not None:
        raise ValueError(f"rejection_reason only allowed for REJECTED, not {new_state.value!r}.")

    updates: dict[str, object] = {
        "state": new_state,
        "updated_at": _utc_now(),
    }
    if rejection_reason is not None:
        updates["rejection_reason"] = rejection_reason
    if rejection_detail is not None:
        updates["rejection_detail"] = rejection_detail
    if cart_id is not None:
        updates["cart_id"] = cart_id
    if cart_hash is not None:
        updates["cart_hash"] = cart_hash
    if amount_paise is not None:
        updates["amount_paise"] = amount_paise
    if nonce is not None:
        updates["nonce"] = nonce
    if razorpay_order_id is not None:
        updates["razorpay_order_id"] = razorpay_order_id
    if razorpay_payment_id is not None:
        updates["razorpay_payment_id"] = razorpay_payment_id
    if step_up_amount_paise is not None:
        updates["step_up_amount_paise"] = step_up_amount_paise
    if new_state is TransactionState.STEP_UP_REQUIRED:
        updates["step_up_required_at"] = _utc_now()
    if new_state is TransactionState.USER_APPROVED:
        updates["step_up_approved_at"] = _utc_now()

    return transaction.model_copy(update=updates)
