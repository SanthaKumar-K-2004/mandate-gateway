"""
Unit tests for Checkout Orchestrator (M24).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.checkout_orchestrator import CheckoutOrchestrator
from apps.api.commerce.models import CheckoutCapability


class TestCheckoutOrchestrator(unittest.TestCase):
    """Checkout Orchestrator test suite."""

    def test_01_prepare_checkout_flow_success(self) -> None:
        """Verify end-to-end checkout preparation flow for valid product candidate."""
        orchestrator = CheckoutOrchestrator()

        raw_candidate = {
            "product_id": "prod_espresso_250",
            "name": "Espresso Roast Coffee 250g",
            "source_url": "https://bluetokaicoffee.com/products/espresso-roast",
            "amount_paise": 48000,
            "currency": "INR",
            "merchant_name": "Blue Tokai Coffee",
            "availability": True,
        }

        success, prep, msg = orchestrator.prepare_checkout_flow(
            request_id="req_test_01",
            buyer_id="buyer_usr_101",
            raw_candidate=raw_candidate,
        )

        self.assertTrue(success)
        self.assertEqual(prep.capability, CheckoutCapability.CHECKOUT_HANDOFF)
        self.assertIsNotNone(prep.confirmation_token)
        self.assertEqual(prep.handoff_url, "https://bluetokaicoffee.com/products/espresso-roast")
        self.assertNotEqual(prep.plan_hash, "")

    def test_02_prepare_checkout_price_mutation_fails(self) -> None:
        """Verify price mutation causes preparation failure and invalidates confirmation token."""
        orchestrator = CheckoutOrchestrator()

        raw_candidate = {
            "product_id": "prod_espresso_250",
            "name": "Espresso Roast Coffee 250g",
            "source_url": "https://bluetokaicoffee.com/products/espresso-roast",
            "amount_paise": 48000,
            "currency": "INR",
        }

        success, prep, msg = orchestrator.prepare_checkout_flow(
            request_id="req_test_02",
            buyer_id="buyer_usr_101",
            raw_candidate=raw_candidate,
            live_recheck_data={"amount_paise": 54000},  # Price mutated!
        )

        self.assertFalse(success)
        self.assertIn("price mutation", msg.lower())
        self.assertIsNone(prep.confirmation_token)
