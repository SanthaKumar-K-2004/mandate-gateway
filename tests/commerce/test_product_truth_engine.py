"""
Unit tests for Product Truth Engine (M24).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.models import ProductVerificationStatus
from apps.api.commerce.product_truth_engine import ProductTruthEngine


class TestProductTruthEngine(unittest.TestCase):
    """Product Truth Engine test suite."""

    def test_01_is_exact_product_url_discrimination(self) -> None:
        """Verify discrimination between product detail pages and collection/home pages."""
        # Product detail URLs
        self.assertTrue(
            ProductTruthEngine.is_exact_product_url(
                "https://bluetokaicoffee.com/products/attikan-estate"
            )
        )
        self.assertTrue(
            ProductTruthEngine.is_exact_product_url("https://cafeacme.local/p/espresso_roast.html")
        )
        self.assertTrue(ProductTruthEngine.is_exact_product_url("https://example.com/item/12345"))

        # Non-product detail URLs
        self.assertFalse(
            ProductTruthEngine.is_exact_product_url(
                "https://bluetokaicoffee.com/collections/coffee"
            )
        )
        self.assertFalse(ProductTruthEngine.is_exact_product_url("https://crossword.in"))
        self.assertFalse(
            ProductTruthEngine.is_exact_product_url("https://example.com/search?q=coffee")
        )

    def test_02_evaluate_valid_product_truth(self) -> None:
        """Verify evaluation of a valid single SKU product candidate."""
        candidate = {
            "product_id": "prod_coffee_101",
            "name": "Attikan Estate Dark Roast 250g",
            "description": "Single origin dark roast",
            "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
            "amount_paise": 48000,
            "currency": "INR",
            "merchant_name": "Blue Tokai Coffee",
            "availability": True,
        }

        truth = ProductTruthEngine.evaluate_product(candidate)
        self.assertTrue(truth.is_sku_verified)
        self.assertTrue(truth.is_price_verified)
        self.assertTrue(truth.is_merchant_verified)
        self.assertEqual(
            truth.product.verification_status, ProductVerificationStatus.PRODUCT_VERIFIED
        )
        self.assertEqual(len(truth.validation_errors), 0)
        self.assertEqual(len(truth.product.evidence_hash), 64)

    def test_03_evaluate_invalid_url_product_truth(self) -> None:
        """Verify category URL produces SOURCE_BACKED status instead of PRODUCT_VERIFIED."""
        candidate = {
            "name": "Coffee Category",
            "source_url": "https://bluetokaicoffee.com/collections/coffee",
            "amount_paise": 48000,
            "currency": "INR",
        }

        truth = ProductTruthEngine.evaluate_product(candidate)
        self.assertFalse(truth.is_sku_verified)
        self.assertEqual(truth.product.verification_status, ProductVerificationStatus.SOURCE_BACKED)
        self.assertTrue(any("collection/listing" in err for err in truth.validation_errors))
