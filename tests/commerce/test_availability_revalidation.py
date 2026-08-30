"""
Unit tests for Live Availability Revalidation Engine (M24).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.availability_revalidation import LiveAvailabilityRevalidator
from apps.api.commerce.product_truth_engine import ProductTruthEngine


class TestAvailabilityRevalidation(unittest.TestCase):
    """Availability Revalidation test suite."""

    def test_01_availability_revalidation_in_stock(self) -> None:
        """Verify in-stock item revalidation passes."""
        candidate = {
            "product_id": "prod_1",
            "name": "Coffee Pack",
            "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
            "amount_paise": 48000,
            "availability": True,
        }
        truth = ProductTruthEngine.evaluate_product(candidate)
        available, ev = LiveAvailabilityRevalidator.revalidate(
            truth.product, {"availability": True}
        )
        self.assertTrue(available)
        self.assertTrue(ev.is_in_stock)

    def test_02_availability_revalidation_out_of_stock(self) -> None:
        """Verify out-of-stock item revalidation fails."""
        candidate = {
            "product_id": "prod_1",
            "name": "Coffee Pack",
            "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
            "amount_paise": 48000,
            "availability": True,
        }
        truth = ProductTruthEngine.evaluate_product(candidate)
        available, ev = LiveAvailabilityRevalidator.revalidate(
            truth.product, {"availability": False}
        )
        self.assertFalse(available)
        self.assertFalse(ev.is_in_stock)
