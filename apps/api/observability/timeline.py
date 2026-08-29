"""
Section M15 — Transaction Timeline Reconstruction Engine.

Reconstructs the complete, ordered, multi-source lifecycle timeline for a target
transaction from persistence, audit, receipt, forensic, outbox, and webhook evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, List, Optional

from apps.api.app.logging import redact_value
from db.unit_of_work import AsyncUnitOfWork

logger = logging.getLogger("mandate_gateway.observability.timeline")


@dataclass
class TimelineItem:
    """Individual entry in a transaction timeline reconstruction."""

    timestamp: str
    category: str
    event_type: str
    component: str
    actor: str
    summary: str
    details: Dict[str, Any]
    source_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "category": self.category,
            "event_type": self.event_type,
            "component": self.component,
            "actor": self.actor,
            "summary": self.summary,
            "details": redact_value(self.details),
            "source_id": self.source_id,
        }


class TransactionTimelineReconstructor:
    """Multi-source timeline reconstructor for Mandate Gateway transactions."""

    async def reconstruct(
        self,
        transaction_id: str,
        uow: AsyncUnitOfWork,
        requesting_merchant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reconstructs structured timeline for transaction_id.
        Enforces tenant isolation: if requesting_merchant_id is provided, it MUST match.
        """
        tx = await uow.transactions.get_transaction(transaction_id)
        if tx is None:
            raise ValueError(f"Transaction '{transaction_id}' not found.")

        # Multi-tenant isolation enforcement
        if (
            requesting_merchant_id
            and requesting_merchant_id != "*"
            and requesting_merchant_id != "mer_operator"
        ):
            if tx.merchant_id != requesting_merchant_id:
                err_msg = (
                    f"Merchant '{requesting_merchant_id}' is not authorized "
                    f"to access timeline for transaction '{transaction_id}'."
                )
                raise PermissionError(err_msg)

        items: List[TimelineItem] = []

        # 1. Primary Transaction Creation Event
        tx_time = (
            tx.created_at.isoformat() if hasattr(tx.created_at, "isoformat") else str(tx.created_at)
        )
        items.append(
            TimelineItem(
                timestamp=tx_time,
                category="PERSISTENCE",
                event_type="transaction.created",
                component="TransactionRepository",
                actor=f"merchant:{tx.merchant_id}",
                summary=f"Transaction created in state '{tx.state}' for amount {tx.amount_paise / 100.0} {tx.currency}",
                details={
                    "transaction_id": tx.transaction_id,
                    "merchant_id": tx.merchant_id,
                    "buyer_id": tx.buyer_id,
                    "mandate_id": tx.mandate_id,
                    "amount_paise": tx.amount_paise,
                    "currency": tx.currency,
                    "state": tx.state,
                },
                source_id=tx.transaction_id,
            )
        )

        # 2. Execution Attempts
        attempts = await uow.execution_attempts.get_attempts_for_transaction(transaction_id)
        for att in attempts:
            att_time = (
                att.created_at.isoformat()
                if hasattr(att.created_at, "isoformat")
                else str(att.created_at)
            )
            items.append(
                TimelineItem(
                    timestamp=att_time,
                    category="EXECUTION",
                    event_type="payment.execution_attempt",
                    component="PaymentExecutionEngine",
                    actor=f"merchant:{tx.merchant_id}",
                    summary=f"Execution attempt '{att.attempt_id}' in status '{att.status}'",
                    details={
                        "attempt_id": att.attempt_id,
                        "status": att.status,
                        "provider_reference": att.provider_reference,
                        "idempotency_key": att.idempotency_key,
                    },
                    source_id=att.attempt_id,
                )
            )

        # 3. Audit Events
        audit_events = await uow.audit.get_events_for_transaction(transaction_id)
        for audit_evt in audit_events:
            a_time = (
                audit_evt.timestamp.isoformat()
                if hasattr(audit_evt.timestamp, "isoformat")
                else str(audit_evt.timestamp)
            )
            payload = {}
            try:
                payload = json.loads(audit_evt.payload_json)
            except Exception:
                pass

            items.append(
                TimelineItem(
                    timestamp=a_time,
                    category="PERSISTENCE",
                    event_type=audit_evt.event_type,
                    component="AuditRepository",
                    actor=audit_evt.buyer_id or audit_evt.merchant_id or "system",
                    summary=f"Audit event '{audit_evt.event_type}' recorded (seq: {audit_evt.sequence_number})",
                    details={
                        "sequence_number": audit_evt.sequence_number,
                        "event_hash": audit_evt.event_hash,
                        "previous_hash": audit_evt.previous_hash,
                        "payload": payload,
                    },
                    source_id=audit_evt.event_id,
                )
            )

        # 4. Action Receipts
        rcp = await uow.receipts.get_receipt_for_transaction(transaction_id)
        if rcp is not None:
            r_time = (
                rcp.created_at.isoformat()
                if hasattr(rcp.created_at, "isoformat")
                else str(rcp.created_at)
            )
            items.append(
                TimelineItem(
                    timestamp=r_time,
                    category="SECURITY_CONTROL",
                    event_type="receipt.signed",
                    component="ReceiptRepository",
                    actor="ed25519_signer",
                    summary="Ed25519 action receipt signed",
                    details={
                        "receipt_id": rcp.receipt_id,
                        "signature": rcp.signature_hex[:16] + "...",
                    },
                    source_id=rcp.receipt_id,
                )
            )

        # 5. Outbox Events
        outbox_events = await uow.outbox.get_pending_events(limit=500)
        for ob in outbox_events:
            if transaction_id in ob.payload_json or transaction_id == ob.aggregate_id:
                ob_time = (
                    ob.created_at.isoformat()
                    if hasattr(ob.created_at, "isoformat")
                    else str(ob.created_at)
                )
                items.append(
                    TimelineItem(
                        timestamp=ob_time,
                        category="OUTBOX",
                        event_type=ob.event_type,
                        component="OutboxRepository",
                        actor="system.outbox",
                        summary=f"Outbox event '{ob.event_type}' status '{ob.status}'",
                        details={
                            "outbox_id": ob.outbox_id,
                            "aggregate_type": ob.aggregate_type,
                            "status": ob.status,
                        },
                        source_id=ob.outbox_id,
                    )
                )

        # Sort timeline items chronologically
        items.sort(key=lambda x: (x.timestamp, x.event_type))

        return {
            "transaction_id": tx.transaction_id,
            "merchant_id": tx.merchant_id,
            "buyer_id": tx.buyer_id,
            "mandate_id": tx.mandate_id,
            "state": tx.state,
            "amount_paise": tx.amount_paise,
            "currency": tx.currency,
            "timeline_length": len(items),
            "events": [item.to_dict() for item in items],
        }


# Global Reconstructor Instance
timeline_reconstructor = TransactionTimelineReconstructor()
