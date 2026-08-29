"""
S06.4 — Provider Status Reconciliation Engine.

Implements safe, multi-worker reconciliation for uncertain or pending payment outcomes:
  1. Queries provider via fetch_payment_status OUTSIDE database locks.
  2. Validates state machine transition rules (no terminal state corruption).
  3. Durably updates internal transaction state via AsyncUnitOfWork.
  4. Appends audit evidence for reconciliation attempts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apps.api.adapters.razorpay_adapter import RazorpayAdapterInterface
from apps.api.domain.audit_ledger import AuditEventType
from apps.api.domain.execution import ExecutionFailureCategory, ExecutionResult
from apps.api.domain.types import (
    PaymentResultState,
    RejectionReason,
    TransactionState,
)
from db.unit_of_work import AsyncUnitOfWork

logger = logging.getLogger("mandate_gateway.reconciliation")


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ReconciliationService:
    """
    Service for resolving uncertain provider outcomes (UNKNOWN / PENDING_RECONCILIATION).

    Key Invariant:
      UNKNOWN outcome != FAILED payment.
      Status reconciliation queries the provider using the durable provider reference
      without issuing duplicate payment charges.
    """

    def __init__(self, adapter: RazorpayAdapterInterface) -> None:
        self._adapter = adapter

    async def async_reconcile_transaction(
        self,
        uow: AsyncUnitOfWork,
        transaction_id: str,
    ) -> ExecutionResult:
        """
        Reconcile transaction status with external provider.
        """
        clean_tx_id = transaction_id.strip()

        # Step 1: Short DB transaction to inspect current state & provider reference
        db_tx = await uow.transactions.lock_transaction_for_update(clean_tx_id)
        if db_tx is None:
            return ExecutionResult(
                success=False,
                transaction_id=clean_tx_id,
                state=TransactionState.REJECTED,
                failure_code=RejectionReason.INVALID_TRANSACTION_STATE,
                failure_category=ExecutionFailureCategory.INVALID_CONTEXT,
                safe_message=f"Transaction '{clean_tx_id}' not found.",
            )

        current_state = TransactionState(db_tx.state)

        # Idempotent return for already terminal transactions
        if current_state in (TransactionState.COMMITTED, TransactionState.SUCCESS):
            return ExecutionResult(
                success=True,
                transaction_id=clean_tx_id,
                state=TransactionState.COMMITTED,
                external_reference=db_tx.provider_payment_id or f"pay_{clean_tx_id[:8]}",
                safe_message="Transaction previously committed successfully.",
                idempotent_replay=True,
                provider_status=PaymentResultState.SUCCESS,
            )

        if current_state in (
            TransactionState.ROLLED_BACK,
            TransactionState.FAILURE,
            TransactionState.REJECTED,
        ):
            return ExecutionResult(
                success=False,
                transaction_id=clean_tx_id,
                state=current_state,
                external_reference=db_tx.provider_payment_id,
                failure_code=RejectionReason.METHOD_NOT_AUTHORIZED,
                failure_category=ExecutionFailureCategory.PROVIDER_REJECTED,
                safe_message="Transaction previously failed or rolled back.",
                idempotent_replay=True,
                provider_status=PaymentResultState.FAILED,
            )

        payment_ref = db_tx.provider_payment_id or clean_tx_id

        # Step 2: Invoke provider status check OUTSIDE database locks
        # Note: uow is not active during network HTTP fetch
        provider_result = self._adapter.fetch_payment_status(payment_ref)

        # Step 3: Short DB transaction to apply reconciled outcome
        if provider_result.provider_status == PaymentResultState.SUCCESS:
            target_state = TransactionState.COMMITTED
            await uow.transactions.transition_transaction_state(clean_tx_id, target_state)
            await uow.audit.append_event(
                event_id=f"evt_rec_{clean_tx_id[:12]}",
                event_type=AuditEventType.PAYMENT_SUCCESS.value,
                transaction_id=clean_tx_id,
                mandate_id=db_tx.mandate_id,
                merchant_id=db_tx.merchant_id,
                buyer_id=db_tx.buyer_id,
                payload={
                    "provider_reference": payment_ref,
                    "reconciled_status": provider_result.provider_status.value,
                },
            )
            return ExecutionResult(
                success=True,
                transaction_id=clean_tx_id,
                state=TransactionState.COMMITTED,
                external_reference=payment_ref,
                safe_message="Reconciliation confirmed payment success.",
                provider_status=PaymentResultState.SUCCESS,
            )

        elif provider_result.provider_status == PaymentResultState.FAILED:
            target_state = TransactionState.ROLLED_BACK
            await uow.transactions.transition_transaction_state(clean_tx_id, target_state)
            await uow.audit.append_event(
                event_id=f"evt_rec_{clean_tx_id[:12]}",
                event_type=AuditEventType.PAYMENT_FAILED.value,
                transaction_id=clean_tx_id,
                mandate_id=db_tx.mandate_id,
                merchant_id=db_tx.merchant_id,
                buyer_id=db_tx.buyer_id,
                payload={
                    "provider_reference": payment_ref,
                    "reconciled_status": provider_result.provider_status.value,
                },
            )
            return ExecutionResult(
                success=False,
                transaction_id=clean_tx_id,
                state=TransactionState.ROLLED_BACK,
                external_reference=payment_ref,
                failure_code=RejectionReason.METHOD_NOT_AUTHORIZED,
                failure_category=ExecutionFailureCategory.PROVIDER_REJECTED,
                safe_message="Reconciliation confirmed payment failure.",
                provider_status=PaymentResultState.FAILED,
            )

        else:
            # Outcome remains UNKNOWN
            return ExecutionResult(
                success=False,
                transaction_id=clean_tx_id,
                state=current_state,
                external_reference=payment_ref,
                failure_code=RejectionReason.AUTHORIZATION_EXPIRED,
                failure_category=ExecutionFailureCategory.TIMEOUT,
                safe_message="Provider status reconciliation returned UNKNOWN. Transaction remains pending.",
                provider_status=PaymentResultState.UNKNOWN,
            )
