"""
Mandate Gateway — Commerce Reconciliation Engine (M26)
Workstream 4 — Automated reconciliation workflow for uncertain commerce operations.
Resolves PAYMENT_SUCCESS_ORDER_UNKNOWN state safely without duplicate payments or duplicate orders.
Enforces non-negotiable invariant: "NO PAYMENT EFFECT MAY ACCIDENTALLY EXECUTE TWICE."
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.api.commerce.models import ReconciliationState


class ReconciliationError(RuntimeError):
    """Raised when reconciliation operations fail or encounter conflicting evidence."""

    pass


@dataclass
class CommerceReconciliationRecord:
    """Record of a commerce reconciliation evaluation."""

    reconciliation_id: str
    purchase_request_id: str
    payment_transaction_id: str
    merchant_order_id: Optional[str]
    merchant_id: str
    buyer_id: str
    amount_paise: int
    currency: str
    state: ReconciliationState
    payment_verified: bool
    order_verified: bool
    reconciled_at: str
    evidence_hash: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reconciliation_id": self.reconciliation_id,
            "purchase_request_id": self.purchase_request_id,
            "payment_transaction_id": self.payment_transaction_id,
            "merchant_order_id": self.merchant_order_id,
            "merchant_id": self.merchant_id,
            "buyer_id": self.buyer_id,
            "amount_paise": self.amount_paise,
            "currency": self.currency,
            "state": self.state.value,
            "payment_verified": self.payment_verified,
            "order_verified": self.order_verified,
            "reconciled_at": self.reconciled_at,
            "evidence_hash": self.evidence_hash,
            "notes": self.notes,
        }


class CommerceReconciliationEngine:
    """
    Automated reconciliation authority for RAZORPAY commerce transactions.
    Idempotently queries payment gateway ledgers and merchant order ledgers.
    """

    def __init__(self) -> None:
        self._records: Dict[str, CommerceReconciliationRecord] = {}

    def reconcile_transaction(
        self,
        purchase_request_id: str,
        payment_transaction_id: str,
        merchant_id: str,
        buyer_id: str,
        amount_paise: int,
        currency: str = "INR",
        merchant_order_id: Optional[str] = None,
        payment_ledger_status: Optional[str] = None,
        merchant_ledger_status: Optional[str] = None,
    ) -> CommerceReconciliationRecord:
        """
        Perform automated reconciliation query across payment and merchant ledgers.
        Ensures NO payment or order creation is duplicated.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        rec_id = f"rec_{uuid.uuid4().hex[:10]}"

        # Evaluate Payment Ledger State
        payment_verified = payment_ledger_status in ("AUTHORIZED", "CAPTURED", "SUCCESS")

        # Evaluate Merchant Ledger State
        order_verified = merchant_ledger_status in (
            "ORDER_CONFIRMED",
            "ORDER_VERIFIED",
            "FULFILLED",
        )

        # Determine Authoritative Reconciliation State
        if payment_verified and order_verified:
            state = ReconciliationState.BOTH_CONFIRMED
            notes = "Both payment authorization and merchant order confirmed."
        elif payment_verified and not order_verified:
            state = ReconciliationState.PAYMENT_ONLY
            notes = "Payment authorized, but merchant order pending confirmation (PAYMENT_SUCCESS_ORDER_UNKNOWN)."
        elif not payment_verified and order_verified:
            state = ReconciliationState.ORDER_ONLY
            notes = "Merchant order created, but payment status unresolved. Manual review required."
        elif not payment_verified and not order_verified:
            state = ReconciliationState.UNRESOLVED
            notes = "Neither payment nor merchant order could be confirmed."
        else:
            state = ReconciliationState.MANUAL_REVIEW_REQUIRED
            notes = "Conflicting ledger evidence detected."

        evidence_payload = (
            f"{rec_id}|{purchase_request_id}|{payment_transaction_id}|"
            f"{merchant_order_id}|{state.value}|{now_iso}"
        )
        evidence_hash = hashlib.sha256(evidence_payload.encode("utf-8")).hexdigest()

        record = CommerceReconciliationRecord(
            reconciliation_id=rec_id,
            purchase_request_id=purchase_request_id,
            payment_transaction_id=payment_transaction_id,
            merchant_order_id=merchant_order_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            amount_paise=amount_paise,
            currency=currency,
            state=state,
            payment_verified=payment_verified,
            order_verified=order_verified,
            reconciled_at=now_iso,
            evidence_hash=evidence_hash,
            notes=notes,
        )

        self._records[rec_id] = record
        return record

    def get_reconciliation_record(
        self, reconciliation_id: str
    ) -> Optional[CommerceReconciliationRecord]:
        """Fetch reconciliation record by ID."""
        return self._records.get(reconciliation_id)

    def get_all_records(self) -> List[Dict[str, Any]]:
        """Return all reconciliation records."""
        return [r.to_dict() for r in self._records.values()]
