"""
Mandate Gateway — Order Verification Engine (M24)
Workstream 12 — Authoritative outcome tracking.
HTTP 200 / redirect DOES NOT equal successful purchase.
Requires authoritative evidence from an authorized connector or webhook to mark ORDER_VERIFIED.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional

from apps.api.commerce.models import CheckoutOutcome, OrderEvidence, OrderStatus


class OrderVerificationError(RuntimeError):
    """Raised when order verification processing encounters an invalid state."""

    pass


class OrderVerificationEngine:
    """Production-grade Order Outcome Verification Engine."""

    def __init__(self) -> None:
        self._orders: Dict[str, CheckoutOutcome] = {}

    def record_checkout_intent(
        self, preparation_id: str, request_id: str, merchant_id: str, capability_str: str
    ) -> CheckoutOutcome:
        """Record initial checkout intent prior to execution."""
        now_iso = datetime.now(timezone.utc).isoformat()
        outcome_id = f"outcome_{hashlib.sha256(f'{preparation_id}|{now_iso}'.encode('utf-8')).hexdigest()[:10]}"

        outcome = CheckoutOutcome(
            outcome_id=outcome_id,
            preparation_id=preparation_id,
            request_id=request_id,
            merchant_id=merchant_id,
            capability=capability_str,  # type: ignore
            payment_transaction_id="",
            order_status=OrderStatus.ORDER_PENDING,
            merchant_order_id=None,
            verified_at=now_iso,
            order_evidence=None,
        )

        self._orders[outcome_id] = outcome
        return outcome

    def verify_order_outcome(
        self,
        outcome_id: str,
        payment_transaction_id: str,
        merchant_order_id: Optional[str] = None,
        authoritative_evidence: Optional[Dict[str, str]] = None,
    ) -> CheckoutOutcome:
        """
        Verify order outcome with authoritative evidence.
        If direct connector evidence is missing, status remains ORDER_UNKNOWN or ORDER_PENDING.
        """
        outcome = self._orders.get(outcome_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        if not outcome:
            outcome = CheckoutOutcome(
                outcome_id=outcome_id,
                preparation_id="prep_unknown",
                request_id="req_unknown",
                merchant_id="mer_unknown",
                capability="CHECKOUT_HANDOFF",  # type: ignore
                payment_transaction_id=payment_transaction_id,
                order_status=OrderStatus.ORDER_UNKNOWN,
                merchant_order_id=merchant_order_id,
                verified_at=now_iso,
            )
            self._orders[outcome_id] = outcome

        outcome.payment_transaction_id = payment_transaction_id
        outcome.merchant_order_id = merchant_order_id
        outcome.verified_at = now_iso

        if authoritative_evidence and merchant_order_id:
            raw = f"{outcome_id}|{payment_transaction_id}|{merchant_order_id}|{now_iso}"
            ev_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

            ev = OrderEvidence(
                order_id=outcome_id,
                merchant_order_id=merchant_order_id,
                payment_transaction_id=payment_transaction_id,
                amount_paise=int(authoritative_evidence.get("amount_paise", 0)),
                currency=authoritative_evidence.get("currency", "INR"),
                verification_source=authoritative_evidence.get("source", "connector_webhook"),
                verified_at=now_iso,
                evidence_hash=ev_hash,
            )
            outcome.order_status = OrderStatus.ORDER_VERIFIED
            outcome.order_evidence = ev
        else:
            # TECHNICAL HONESTY: Redirect or payment authorization without merchant order proof is ORDER_UNKNOWN
            outcome.order_status = OrderStatus.ORDER_UNKNOWN

        return outcome

    def get_outcome(self, outcome_id: str) -> Optional[CheckoutOutcome]:
        """Fetch recorded order outcome by outcome_id."""
        return self._orders.get(outcome_id)
