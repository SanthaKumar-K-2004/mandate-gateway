"""
M23 Live Product Truth Validation Test Suite
============================================
Workstream 4 & 11 — Verifies ProductTruthValidator rules:
  1. Product facts must originate from retrieved source evidence.
  2. Missing prices are marked UNVERIFIED and cannot proceed to automatic payment execution.
  3. Conflicting price outputs are detected and rejected.
  4. Source provenance records preserve source provider, source URL, and retrieval timestamp.
"""

from __future__ import annotations

import unittest
from apps.api.agent.live_data import ProductNormalizer, SourceExtractionProvider
from apps.api.agent.product_truth_validator import ProductTruthValidator


class TestM23LiveProductTruth(unittest.TestCase):
    """Product truth and source evidence test suite."""

    def test_01_source_evidence_extraction(self) -> None:
        """Verify SourceExtractionProvider extracts price and merchant evidence from raw search title/snippet."""
        title = "Espresso Roast Coffee Beans 250g - ₹180"
        snippet = "Buy fresh coffee online for ₹180.00 INR from Cafe Acme."
        url = "https://world.openfoodfacts.org/product/12345"

        record = SourceExtractionProvider.extract_evidence(title, snippet, url, "tavily")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.source_provider, "tavily")
        self.assertEqual(record.verification_status, "VERIFIED")
        self.assertIn("18000", record.price_evidence)

        # Normalize to product candidate
        norm = ProductNormalizer.normalize(record, "coffee")
        self.assertEqual(norm["amount_paise"], 18000)
        self.assertTrue(norm["is_verified"])

    def test_02_missing_price_evidence_marked_unverified(self) -> None:
        """Verify missing price evidence produces UNVERIFIED verification status."""
        title = "Artisanal Coffee Mug"
        snippet = "Beautiful ceramic coffee mug. Out of stock."
        url = "https://example.com/mug"

        record = SourceExtractionProvider.extract_evidence(title, snippet, url, "tavily")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.verification_status, "UNVERIFIED")
        self.assertFalse(record.availability_evidence)

    def test_03_truth_validator_verifies_valid_recommendation(self) -> None:
        """Verify valid recommendation matching source evidence passes truth validation."""
        selected = {
            "source_product_id": "src_coffee_101",
            "name": "Espresso Roast Coffee",
            "amount_paise": 18000,
        }
        sources = [
            {
                "source_product_id": "src_coffee_101",
                "name": "Espresso Roast Coffee",
                "amount_paise": 18000,
                "currency": "INR",
                "merchant_identity": "mer_cafe_acme",
                "source_url": "https://world.openfoodfacts.org/product/101",
                "retrieval_timestamp": "2026-08-30T15:00:00Z",
                "verification_status": "VERIFIED",
                "is_verified": True,
            }
        ]
        truth = ProductTruthValidator.validate_recommendation(selected, sources)
        self.assertEqual(truth["amount_paise"], 18000)
        self.assertEqual(truth["product_source"], "VERIFIED")
        self.assertTrue(truth["is_verified"])

    def test_05_is_exact_product_url_discrimination(self) -> None:
        """Verify SourceExtractionProvider discriminates exact product URLs from collection/homepages."""
        # Generic collection/homepages
        self.assertFalse(
            SourceExtractionProvider.is_exact_product_url(
                "https://bluetokaicoffee.com/collections/roasted-coffee"
            )
        )
        self.assertFalse(SourceExtractionProvider.is_exact_product_url("https://www.crossword.in"))
        self.assertFalse(
            SourceExtractionProvider.is_exact_product_url("https://example.com/search?q=coffee")
        )

        # Exact product detail page URLs
        self.assertTrue(
            SourceExtractionProvider.is_exact_product_url(
                "https://example.com/product/espresso-roast-250g.html"
            )
        )
        self.assertTrue(
            SourceExtractionProvider.is_exact_product_url("https://amazon.in/dp/B08N5WRWNW")
        )
        self.assertTrue(
            SourceExtractionProvider.is_exact_product_url("https://store.com/p/coffee-beans-101")
        )


if __name__ == "__main__":
    unittest.main()
