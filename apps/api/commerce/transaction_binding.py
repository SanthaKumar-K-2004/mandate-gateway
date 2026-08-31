"""
Mandate Gateway — Transaction Binding Manager (M25)
Workstream 2 — Enforces strict 1:1 binding between Payment Transactions and Merchant Orders.
Rejects duplicate transaction bindings or cross-order reuse.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional


class TransactionBindingError(RuntimeError):
    """Raised when transaction binding rules are violated."""

    pass


@dataclass
class CommerceTransactionBinding:
    """1:1 Binding between RAZERPAY Payment Transaction and Merchant Order."""

    binding_id: str
    razerpay_transaction_id: str
    merchant_order_id: str
    merchant_id: str
    product_id: str
    product_evidence_hash: str
    order_binding_hash: str
    payment_amount_paise: int
    currency: str
    connector_id: str
    created_at: str
    status: str = "BOUND"  # BOUND, RELEASED, INVALIDATED

    def to_dict(self) -> Dict[str, str | int]:
        return {
            "binding_id": self.binding_id,
            "razerpay_transaction_id": self.razerpay_transaction_id,
            "merchant_order_id": self.merchant_order_id,
            "merchant_id": self.merchant_id,
            "product_id": self.product_id,
            "product_evidence_hash": self.product_evidence_hash,
            "order_binding_hash": self.order_binding_hash,
            "payment_amount_paise": self.payment_amount_paise,
            "currency": self.currency,
            "connector_id": self.connector_id,
            "created_at": self.created_at,
            "status": self.status,
        }


class CommerceTransactionBindingManager:
    """Manager for Payment ↔ Merchant Order bindings."""

    def __init__(self) -> None:
        self._tx_map: Dict[str, CommerceTransactionBinding] = {}
        self._order_map: Dict[str, CommerceTransactionBinding] = {}

    def bind_transaction_to_order(
        self,
        binding_id: str,
        razerpay_transaction_id: str,
        merchant_order_id: str,
        merchant_id: str,
        product_id: str,
        product_evidence_hash: str,
        order_binding_hash: str,
        payment_amount_paise: int,
        currency: str,
        connector_id: str,
    ) -> CommerceTransactionBinding:
        """
        Create 1:1 binding between Payment Transaction and Merchant Order.
        Fails if payment transaction or merchant order is already bound to another entity.
        """
        if razerpay_transaction_id in self._tx_map:
            existing = self._tx_map[razerpay_transaction_id]
            if existing.merchant_order_id != merchant_order_id:
                raise TransactionBindingError(
                    f"Transaction '{razerpay_transaction_id}' is already bound to "
                    f"merchant order '{existing.merchant_order_id}'."
                )

        if merchant_order_id in self._order_map:
            existing = self._order_map[merchant_order_id]
            if existing.razerpay_transaction_id != razerpay_transaction_id:
                raise TransactionBindingError(
                    f"Merchant order '{merchant_order_id}' is already bound to "
                    f"transaction '{existing.razerpay_transaction_id}'."
                )

        now_iso = datetime.now(timezone.utc).isoformat()
        binding = CommerceTransactionBinding(
            binding_id=binding_id,
            razerpay_transaction_id=razerpay_transaction_id,
            merchant_order_id=merchant_order_id,
            merchant_id=merchant_id,
            product_id=product_id,
            product_evidence_hash=product_evidence_hash,
            order_binding_hash=order_binding_hash,
            payment_amount_paise=payment_amount_paise,
            currency=currency,
            connector_id=connector_id,
            created_at=now_iso,
            status="BOUND",
        )

        self._tx_map[razerpay_transaction_id] = binding
        self._order_map[merchant_order_id] = binding
        return binding

    def get_binding_by_transaction(
        self, razerpay_transaction_id: str
    ) -> Optional[CommerceTransactionBinding]:
        """Fetch binding by payment transaction ID."""
        return self._tx_map.get(razerpay_transaction_id)

    def get_binding_by_order(self, merchant_order_id: str) -> Optional[CommerceTransactionBinding]:
        """Fetch binding by merchant order ID."""
        return self._order_map.get(merchant_order_id)
