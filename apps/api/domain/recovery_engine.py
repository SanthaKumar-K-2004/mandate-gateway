"""
M07 — Transaction Recovery & Provider Reconciliation Engine.

Detects, reconciles, and recovers stuck or unconfirmed transactions in intermediate
states (e.g. EXECUTING) after worker crashes, network timeouts, or process restarts.

Core Invariants:
  - Fail-closed: If provider status cannot be proven to be SUCCESS or FAILED,
    the transaction remains in EXECUTING state. Blind duplicate charges are strictly prohibited.
  - Exactly-once effect reconciliation: Queries provider state using external order/payment ID.
  - Transactional outbox & audit evidence: Generates audit events and outbox side effects.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Sequence

from apps.api.adapters.razorpay_adapter import RazorpayAdapterInterface
from apps.api.domain.types import (
    AuditEventType,
    PaymentResultState,
    TransactionState,
)

if TYPE_CHECKING:
    from db.unit_of_work import AsyncUnitOfWork

logger = logging.getLogger("mandate_gateway.recovery")


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class RecoveryRecord:
    """Diagnostic outcome record for a single transaction recovery attempt."""

    transaction_id: str
    previous_state: str
    final_state: str
    provider_status: str
    recovered: bool
    message: str
    timestamp: datetime = field(default_factory=_utc_now)


class TransactionRecoveryService:
    """
    Service for automatic recovery and reconciliation of stuck transactions.
    """

    def __init__(self, adapter: RazorpayAdapterInterface) -> None:
        self.adapter = adapter

    async def scan_stuck_transactions(
        self,
        uow: AsyncUnitOfWork,
        stuck_threshold_seconds: int = 30,
        at: datetime | None = None,
    ) -> Sequence[str]:
        """
        Scan persistence store for transactions in EXECUTING state that have not been
        updated within stuck_threshold_seconds.
        """
        now = at if at is not None else _utc_now()
        cutoff = now - timedelta(seconds=stuck_threshold_seconds)
        stuck_txs = await uow.transactions.list_transactions_requiring_reconciliation(cutoff)
        return [tx.transaction_id for tx in stuck_txs]

    async def reconcile_transaction(
        self,
        uow: AsyncUnitOfWork,
        transaction_id: str,
    ) -> RecoveryRecord:
        """
        Reconcile a single in-flight transaction with the external provider.

        Steps:
          1. Lock transaction row in DB.
          2. If already terminal (COMMITTED / ROLLED_BACK), return early.
          3. Query adapter for payment status.
          4. If SUCCESS: transition EXECUTING -> COMMITTED, write audit & outbox events.
          5. If FAILED/EXPIRED: transition EXECUTING -> ROLLED_BACK, write audit & outbox events.
          6. If UNKNOWN: remain in EXECUTING state (fail-closed).
        """
        tx = await uow.transactions.lock_transaction_for_update(transaction_id)
        if tx is None:
            return RecoveryRecord(
                transaction_id=transaction_id,
                previous_state="UNKNOWN",
                final_state="UNKNOWN",
                provider_status="NOT_FOUND",
                recovered=False,
                message=f"Transaction '{transaction_id}' not found in database.",
            )

        prev_state = tx.state

        # Terminal state guard
        if tx.state in (
            TransactionState.COMMITTED.value,
            TransactionState.ROLLED_BACK.value,
            TransactionState.REJECTED.value,
        ):
            return RecoveryRecord(
                transaction_id=transaction_id,
                previous_state=prev_state,
                final_state=tx.state,
                provider_status=tx.provider_status or "TERMINAL",
                recovered=True,
                message=f"Transaction '{transaction_id}' already in terminal state '{tx.state}'.",
            )

        ref = tx.provider_payment_id or transaction_id
        provider_res = self.adapter.fetch_payment_status(ref)

        if provider_res.provider_status == PaymentResultState.SUCCESS:
            await uow.transactions.record_provider_outcome(
                transaction_id,
                provider_status="SUCCESS",
                provider_payment_id=ref,
            )
            await uow.transactions.transition_transaction_state(
                transaction_id, TransactionState.COMMITTED
            )
            await uow.audit.append_event(
                AuditEventType.PAYMENT_SUCCESS,
                transaction_id=transaction_id,
                merchant_id=tx.merchant_id,
                buyer_id=tx.buyer_id,
                mandate_id=tx.mandate_id,
                payload={
                    "reconciliation": True,
                    "provider_reference": ref,
                    "recovered_from": prev_state,
                },
            )
            await uow.outbox.create_event(
                event_type="PAYMENT_COMMITTED",
                aggregate_type="TRANSACTION",
                aggregate_id=transaction_id,
                payload={
                    "transaction_id": transaction_id,
                    "merchant_id": tx.merchant_id,
                    "amount_paise": tx.amount_paise,
                    "reconciled": True,
                },
            )
            logger.info(
                "Successfully recovered stuck transaction '%s' to COMMITTED.", transaction_id
            )
            return RecoveryRecord(
                transaction_id=transaction_id,
                previous_state=prev_state,
                final_state=TransactionState.COMMITTED.value,
                provider_status="SUCCESS",
                recovered=True,
                message="Status successfully reconciled to COMMITTED.",
            )

        elif provider_res.provider_status in (
            PaymentResultState.FAILED,
            PaymentResultState.EXPIRED,
        ):
            await uow.transactions.record_provider_outcome(
                transaction_id,
                provider_status="FAILED",
                provider_payment_id=ref,
            )
            await uow.transactions.transition_transaction_state(
                transaction_id, TransactionState.FAILURE
            )
            await uow.transactions.transition_transaction_state(
                transaction_id, TransactionState.ROLLED_BACK
            )
            await uow.audit.append_event(
                AuditEventType.PAYMENT_FAILED,
                transaction_id=transaction_id,
                merchant_id=tx.merchant_id,
                buyer_id=tx.buyer_id,
                mandate_id=tx.mandate_id,
                payload={
                    "reconciliation": True,
                    "provider_reference": ref,
                    "recovered_from": prev_state,
                },
            )
            await uow.outbox.create_event(
                event_type="PAYMENT_ROLLED_BACK",
                aggregate_type="TRANSACTION",
                aggregate_id=transaction_id,
                payload={
                    "transaction_id": transaction_id,
                    "merchant_id": tx.merchant_id,
                    "amount_paise": tx.amount_paise,
                    "reconciled": True,
                },
            )
            logger.info(
                "Successfully recovered stuck transaction '%s' to ROLLED_BACK.", transaction_id
            )
            return RecoveryRecord(
                transaction_id=transaction_id,
                previous_state=prev_state,
                final_state=TransactionState.ROLLED_BACK.value,
                provider_status="FAILED",
                recovered=True,
                message="Status successfully reconciled to ROLLED_BACK.",
            )

        else:
            # Remains UNKNOWN: maintain EXECUTING state fail-closed
            logger.warning(
                "Transaction '%s' reconciliation returned UNKNOWN. Maintaining EXECUTING state.",
                transaction_id,
            )
            return RecoveryRecord(
                transaction_id=transaction_id,
                previous_state=prev_state,
                final_state=TransactionState.EXECUTING.value,
                provider_status="UNKNOWN",
                recovered=False,
                message="Provider status remains UNKNOWN. Transaction preserved in EXECUTING state.",
            )

    async def recover_all_stuck(
        self,
        uow: AsyncUnitOfWork,
        stuck_threshold_seconds: int = 30,
    ) -> list[RecoveryRecord]:
        """
        Scan and attempt recovery for all stuck transactions.
        """
        stuck_ids = await self.scan_stuck_transactions(
            uow, stuck_threshold_seconds=stuck_threshold_seconds
        )
        results: list[RecoveryRecord] = []
        for tx_id in stuck_ids:
            rec = await self.reconcile_transaction(uow, tx_id)
            results.append(rec)
        return results
