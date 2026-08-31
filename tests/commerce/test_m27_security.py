"""
Unit tests for Milestone M27 Security & Adversarial Threat Model Rules.
"""

from __future__ import annotations

import unittest

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.models import CheckoutCapability
from apps.api.commerce.recommendation_engine import DeterministicRecommendationEngine


class TestM27Security(unittest.TestCase):
    """M27 Security & Adversarial Threat Model test suite."""

    def test_01_llm_recommendation_tampering_prevented(self) -> None:
        """Verify deterministic recommendation score cannot be tampered with by zero price or fake URL."""
        engine = DeterministicRecommendationEngine()

        fake_zero_price = CanonicalProduct.create(
            product_id="prod_malicious_01",
            title="Free Coffee Hack",
            price_paise=0,  # invalid price
            merchant_name="Hacker Store",
            merchant_domain="hacker.com",
            product_url="https://hacker.com/free",
            source_provider="Malicious Provider",
            checkout_capability=CheckoutCapability.VERIFIED_API,
        )

        best, scored, status = engine.rank_candidates([fake_zero_price], max_price_paise=20000)
        self.assertIsNone(best)
        self.assertIn("No sufficiently verified products", status)

    def test_02_ssrf_malicious_product_url_rejected(self) -> None:
        """Verify products with non-HTTP/HTTPS URLs are rejected by recommendation engine."""
        engine = DeterministicRecommendationEngine()

        ssrf_item = CanonicalProduct.create(
            product_id="prod_ssrf_01",
            title="SSRF Attempt Coffee",
            price_paise=10000,
            merchant_name="Internal Admin",
            merchant_domain="localhost",
            product_url="file:///etc/passwd",  # malicious file scheme
            source_provider="SSRF Injector",
            checkout_capability=CheckoutCapability.VERIFIED_API,
        )

        best, scored, status = engine.rank_candidates([ssrf_item], max_price_paise=20000)
        self.assertIsNone(best)
