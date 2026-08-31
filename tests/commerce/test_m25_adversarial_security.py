"""
Adversarial Security Test Matrix for M25 (Real Merchant Connector, Order & Transaction Binding, Webhooks).
"""

from __future__ import annotations

import hashlib
import hmac
import time
import unittest
from typing import Any, Dict

from apps.api.commerce.order_binding import CommerceOrderBinder
from apps.api.commerce.transaction_binding import (
    CommerceTransactionBindingManager,
    TransactionBindingError,
)
from apps.api.commerce.webhooks import CommerceWebhookHandler, WebhookValidationError


class TestM25AdversarialSecurity(unittest.TestCase):
    """Adversarial Security Test Suite for M25 features."""

    def test_adv_01_product_substitution_attack_blocked(self) -> None:
        """Verify product substitution attack (confirming Product A, ordering Product B) fails binding verification."""
        binder = CommerceOrderBinder(secret_key="m25_adv_secret")

        legit_payload: Dict[str, Any] = {
            "purchase_request_id": "req_adv_01",
            "merchant_id": "mer_cafe_acme",
            "buyer_id": "buyer_legit",
            "product_id": "prod_tea_01",
            "quantity": 1,
            "amount_paise": 14000,
            "currency": "INR",
            "merchant_order_id": "m_ord_101",
            "payment_reference": "txn_pay_101",
            "plan_hash": "plan_hash_01",
        }

        binding_hash = binder.compute_binding_hash(
            purchase_request_id=str(legit_payload["purchase_request_id"]),
            merchant_id=str(legit_payload["merchant_id"]),
            buyer_id=str(legit_payload["buyer_id"]),
            product_id=str(legit_payload["product_id"]),
            quantity=int(str(legit_payload["quantity"])),
            amount_paise=int(str(legit_payload["amount_paise"])),
            currency=str(legit_payload["currency"]),
            merchant_order_id=str(legit_payload["merchant_order_id"]),
            payment_reference=str(legit_payload["payment_reference"]),
            plan_hash=str(legit_payload["plan_hash"]),
        )

        # Attacker attempts to substitute product_id
        substituted = dict(legit_payload)
        substituted["product_id"] = "prod_expensive_laptop_999"
        self.assertFalse(binder.verify_binding(substituted, binding_hash))

    def test_adv_02_duplicate_payment_transaction_reuse_blocked(self) -> None:
        """Verify reusing an authorized payment transaction ID across multiple orders is blocked."""
        mgr = CommerceTransactionBindingManager()

        mgr.bind_transaction_to_order(
            binding_id="bind_legit",
            razerpay_transaction_id="txn_stolen_pay_99",
            merchant_order_id="m_ord_legit_01",
            merchant_id="mer_cafe_acme",
            product_id="prod_tea_01",
            product_evidence_hash="ev_01",
            order_binding_hash="ord_01",
            payment_amount_paise=14000,
            currency="INR",
            connector_id="connector_cafe_acme_api",
        )

        # Attacker attempts to reuse txn_stolen_pay_99 for another order
        with self.assertRaises(TransactionBindingError):
            mgr.bind_transaction_to_order(
                binding_id="bind_attack",
                razerpay_transaction_id="txn_stolen_pay_99",
                merchant_order_id="m_ord_attacker_99",
                merchant_id="mer_malicious",
                product_id="prod_laptop_99",
                product_evidence_hash="ev_99",
                order_binding_hash="ord_99",
                payment_amount_paise=14000,
                currency="INR",
                connector_id="connector_cafe_acme_api",
            )

    def test_adv_03_unauthenticated_webhook_injection_blocked(self) -> None:
        """Verify unauthenticated merchant webhook injection is rejected."""
        handler = CommerceWebhookHandler(webhook_secret="whsec_m25_secret")
        raw_body = b'{"event": "order.confirmed", "merchant_order_id": "m_ord_spoofed"}'

        with self.assertRaises(WebhookValidationError):
            handler.process_webhook(
                raw_body=raw_body,
                signature="sha256=invalid_spoofed_signature",
                event_id="evt_spoof_01",
                timestamp_header=str(int(time.time())),
                payload={},
            )

    def test_adv_04_webhook_replay_attack_blocked(self) -> None:
        """Verify replaying an old webhook (> 300s) is blocked."""
        secret = "whsec_m25_secret"
        handler = CommerceWebhookHandler(webhook_secret=secret)

        old_timestamp = int(time.time()) - 600  # 10 minutes old!
        raw_body = b'{"event": "order.confirmed"}'
        sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        with self.assertRaises(WebhookValidationError):
            handler.process_webhook(
                raw_body=raw_body,
                signature=f"sha256={sig}",
                event_id="evt_replay_01",
                timestamp_header=str(old_timestamp),
                payload={},
            )
