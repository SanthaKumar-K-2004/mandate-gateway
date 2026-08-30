"""
Unit tests for Live Price Revalidation Engine (M24).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.price_revalidation import LivePriceRevalidator
from apps.api.commerce.product_truth_engine import ProductTruthEngine


class TestPriceRevalidation(unittest.TestCase):
    """Price Revalidation test suite."""

    def test_01_price_revalidation_unchanged(self) -> None:
        """Verify price revalidation passes when live price is unchanged."""
        candidate = {
            "product_id": "prod_1",
            "name": "Coffee Pack",
            "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
            "amount_paise": 48000,
            "currency": "INR",
        }
        truth = ProductTruthEngine.evaluate_product(candidate)
        valid, cur_price, price_changed = LivePriceRevalidator.revalidate(
            truth.product, {"amount_paise": 48000}
        )

        self.assertTrue(valid)
        self.assertFalse(price_changed)
        self.assertEqual(cur_price.amount_paise, 48000)

    def test_02_price_mutation_detected(self) -> None:
        """Verify price mutation (e.g. 48000 -> 54000) causes revalidation failure and marks price_changed=True."""
        candidate = {
            "product_id": "prod_1",
            "name": "Coffee Pack",
            "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
            "amount_paise": 48000,
            "currency": "INR",
        }
        truth = ProductTruthEngine.evaluate_product(candidate)
        valid, cur_price, price_changed = LivePriceRevalidator.revalidate(
            truth.product, {"amount_paise": 54000}
        )

        self.assertFalse(valid)
        self.assertTrue(price_changed)
        self.assertEqual(cur_price.amount_paise, 54000)
