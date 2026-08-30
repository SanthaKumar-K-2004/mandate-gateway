"""
Adversarial Security Test Matrix for Commerce Truth & Verified Checkout (M24).
Tests malicious input vectors, open redirects, price attacks, token replay, and capability spoofing.
"""

from __future__ import annotations

import unittest

from apps.api.commerce.connector_registry import CommerceConnectorRegistry
from apps.api.commerce.connectors.base import CommerceConnectorError
from apps.api.commerce.connectors.generic_web import GenericWebCheckoutConnector
from apps.api.commerce.price_revalidation import LivePriceRevalidator
from apps.api.commerce.product_truth_engine import ProductTruthEngine
from apps.api.commerce.redirect_handoff import SecureRedirectHandoffManager


class TestAdversarialCommerceSecurity(unittest.TestCase):
    """Adversarial Security Test Suite for Commerce domain."""

    def test_adv_01_open_redirect_defense(self) -> None:
        """Verify URL validator blocks open redirects, javascript: schemes, data: URIs, file: URLs, and loopbacks."""
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
            "file:///etc/passwd",
            "http://localhost:8000/admin",
            "http://127.0.0.1/secret",
            "http://169.254.169.254/latest/meta-data/",
        ]

        for url in dangerous_urls:
            with self.assertRaises(CommerceConnectorError):
                GenericWebCheckoutConnector.validate_handoff_url(url)

    def test_adv_02_price_mutation_attack_mitigation(self) -> None:
        """Verify price mutation (e.g. ₹180 to ₹240) invalidates checkout preparation."""
        candidate = {
            "product_id": "prod_coffee_101",
            "name": "Coffee Pack",
            "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
            "amount_paise": 18000,
        }
        truth = ProductTruthEngine.evaluate_product(candidate)
        valid, cur_price, price_changed = LivePriceRevalidator.revalidate(
            truth.product, {"amount_paise": 24000}
        )

        self.assertFalse(valid)
        self.assertTrue(price_changed)
        self.assertEqual(cur_price.amount_paise, 24000)

    def test_adv_03_redirect_handoff_signature_tampering(self) -> None:
        """Verify tampered redirect handoff package fails signature verification."""
        manager = SecureRedirectHandoffManager(secret_key="secret_test_key")
        truth = ProductTruthEngine.evaluate_product(
            {
                "product_id": "prod_101",
                "name": "Coffee",
                "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
                "amount_paise": 48000,
            }
        )

        pkg = manager.create_handoff_package(
            request_id="req_88", buyer_id="buyer_1", product=truth.product
        )
        self.assertTrue(manager.verify_handoff_package(pkg))

        # Tamper with price in payload
        pkg_tampered = dict(pkg)
        pkg_tampered["amount_paise"] = 1000  # Try to pay 10 INR instead of 480 INR!
        self.assertFalse(manager.verify_handoff_package(pkg_tampered))

    def test_adv_04_connector_capability_spoofing_defense(self) -> None:
        """Verify an unauthorized connector cannot register for an already bound domain."""
        registry = CommerceConnectorRegistry()

        class FakeSpoofConnector(GenericWebCheckoutConnector):
            @property
            def connector_id(self) -> str:
                return "connector_spoof"

        c1 = GenericWebCheckoutConnector()
        c2 = FakeSpoofConnector()

        registry.register_connector(c1, target_domains=["bluetokaicoffee.com"])

        with self.assertRaises(CommerceConnectorError):
            registry.register_connector(c2, target_domains=["bluetokaicoffee.com"])
