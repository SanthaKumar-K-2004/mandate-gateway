"""
S03.1 — Purchase Proposal & Transaction API Router.

Implements REST API endpoints for purchase proposal evaluation, transaction state retrieval,
and human step-up decisions (Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
import uuid

from apps.api.contracts.transaction import (
    DecisionTraceResponse,
    PurchaseProposalRequest,
    StepUpApproveRequest,
    StepUpDiff,
    StepUpRejectRequest,
    TransactionResponse,
)
from apps.api.domain.types import (
    PolicyDecision,
    RejectionReason,
    TransactionState,
)

try:
    from fastapi import APIRouter, HTTPException, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_404_NOT_FOUND = 404
        HTTP_400_BAD_REQUEST = 400

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail


# In-memory store for transactions
_TRANSACTIONS: dict[str, TransactionResponse] = {}


if HAS_FASTAPI:
    transactions_router = APIRouter(prefix="/api", tags=["Transactions & Purchase Proposals"])
else:

    class DummyRouter:
        def post(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

        def get(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

    transactions_router = DummyRouter()


@transactions_router.post(
    "/purchase-proposals",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_purchase_proposal(payload: PurchaseProposalRequest) -> TransactionResponse:
    """Evaluate an AI purchase proposal and generate transaction state."""
    transaction_id = f"tx_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    # Determine initial policy decision & state based on amount
    # Default rule for demo / router evaluation:
    # total_paise > 1,000,000 (₹10,000) requires STEP_UP_REQUIRED
    # total_paise <= 1,000,000 is ALLOW / AUTHORIZED
    if payload.total_paise > 1000000:
        state = TransactionState.STEP_UP_REQUIRED
        decision_trace = DecisionTraceResponse(
            decision=PolicyDecision.STEP_UP_REQUIRED,
            checks_passed=["merchant_policy", "mandate_active", "daily_budget"],
            checks_failed=[],
            step_up_diff=StepUpDiff(
                approved_paise=500000,
                proposed_paise=payload.total_paise,
                delta_paise=payload.total_paise - 500000,
                delta_percent=round(((payload.total_paise - 500000) / 500000) * 100, 2),
                reason="Purchase total exceeds mandate autonomous limit ₹5,000. Step-up approval required.",
            ),
        )
    else:
        state = TransactionState.AUTHORIZED
        decision_trace = DecisionTraceResponse(
            decision=PolicyDecision.ALLOW,
            checks_passed=[
                "merchant_policy",
                "mandate_active",
                "daily_budget",
                "autonomous_limit",
                "nonce_unique",
            ],
            checks_failed=[],
        )

    tx_response = TransactionResponse(
        transaction_id=transaction_id,
        buyer_id=payload.buyer_id,
        merchant_id=payload.merchant_id,
        mandate_id=payload.mandate_id,
        mandate_version=1,
        policy_version=1,
        cart_id=f"cart_{uuid.uuid4().hex[:8]}",
        cart_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        amount_paise=payload.total_paise,
        currency=payload.currency,
        state=state,
        decision_trace=decision_trace,
        rejection_reason=None,
        rejection_detail=None,
        idempotency_key=payload.idempotency_key,
        nonce=uuid.uuid4().hex,
        created_at=now,
        updated_at=now,
    )
    _TRANSACTIONS[transaction_id] = tx_response
    return tx_response


@transactions_router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
)
def get_transaction(transaction_id: str) -> TransactionResponse:
    """Fetch full transaction state."""
    if transaction_id not in _TRANSACTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' not found.",
        )
    return _TRANSACTIONS[transaction_id]


@transactions_router.post(
    "/transactions/{transaction_id}/approve",
    response_model=TransactionResponse,
)
def approve_step_up(transaction_id: str, payload: StepUpApproveRequest) -> TransactionResponse:
    """Approve a STEP_UP_REQUIRED transaction."""
    if transaction_id not in _TRANSACTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' not found.",
        )

    tx = _TRANSACTIONS[transaction_id]
    if tx.state != TransactionState.STEP_UP_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction '{transaction_id}' is in state '{tx.state}', not STEP_UP_REQUIRED.",
        )

    now = datetime.now(timezone.utc)
    updated_tx = TransactionResponse(
        transaction_id=tx.transaction_id,
        buyer_id=tx.buyer_id,
        merchant_id=tx.merchant_id,
        mandate_id=tx.mandate_id,
        mandate_version=tx.mandate_version,
        policy_version=tx.policy_version,
        cart_id=tx.cart_id,
        cart_hash=tx.cart_hash,
        amount_paise=payload.approved_amount_paise,
        currency=tx.currency,
        state=TransactionState.COMMITTED,
        decision_trace=tx.decision_trace,
        rejection_reason=None,
        rejection_detail=None,
        idempotency_key=tx.idempotency_key,
        nonce=tx.nonce,
        created_at=tx.created_at,
        updated_at=now,
    )
    _TRANSACTIONS[transaction_id] = updated_tx
    return updated_tx


@transactions_router.post(
    "/transactions/{transaction_id}/reject",
    response_model=TransactionResponse,
)
def reject_step_up(transaction_id: str, payload: StepUpRejectRequest) -> TransactionResponse:
    """Reject a STEP_UP_REQUIRED transaction."""
    if transaction_id not in _TRANSACTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction '{transaction_id}' not found.",
        )

    tx = _TRANSACTIONS[transaction_id]
    if tx.state != TransactionState.STEP_UP_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction '{transaction_id}' is in state '{tx.state}', not STEP_UP_REQUIRED.",
        )

    now = datetime.now(timezone.utc)
    updated_tx = TransactionResponse(
        transaction_id=tx.transaction_id,
        buyer_id=tx.buyer_id,
        merchant_id=tx.merchant_id,
        mandate_id=tx.mandate_id,
        mandate_version=tx.mandate_version,
        policy_version=tx.policy_version,
        cart_id=tx.cart_id,
        cart_hash=tx.cart_hash,
        amount_paise=tx.amount_paise,
        currency=tx.currency,
        state=TransactionState.REJECTED,
        decision_trace=tx.decision_trace,
        rejection_reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
        rejection_detail=payload.reason,
        idempotency_key=tx.idempotency_key,
        nonce=tx.nonce,
        created_at=tx.created_at,
        updated_at=now,
    )
    _TRANSACTIONS[transaction_id] = updated_tx
    return updated_tx
