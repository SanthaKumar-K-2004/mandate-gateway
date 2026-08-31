"""
Unit tests for Product Deduplication Engine (M27).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.canonical_product import CanonicalProduct
from apps.api.commerce.models import CheckoutCapability
from apps.api.commerce.product_deduplication import ProductDeduplicator


class TestProductDeduplication(unittest.TestCase):
    """ProductDeduplicator test suite."""

    def test_01_deduplicate_exact_url_match(self) -> None:
        """Verify duplicate candidates with exact same product URL are merged."""
        dedup = ProductDeduplicator()

        c1 = CanonicalProduct.create(
            product_id="prod_01",
            title="Espresso Coffee Beans",
            price_paise=18000,
            merchant_name="Merchant A",
            merchant_domain="shop.com",
            product_url="https://shop.com/item1",
            source_provider="Provider A",
            checkout_capability=CheckoutCapability.CHECKOUT_HANDOFF,
        )
        c2 = CanonicalProduct.create(
            product_id="prod_02",
            title="Espresso Coffee Beans",
            price_paise=18000,
            merchant_name="Merchant A",
            merchant_domain="shop.com",
            product_url="https://shop.com/item1",
            source_provider="Provider B",
            checkout_capability=CheckoutCapability.VERIFIED_API,  # higher quality
        )

        res = dedup.deduplicate([c1, c2])
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].checkout_capability, CheckoutCapability.VERIFIED_API)
