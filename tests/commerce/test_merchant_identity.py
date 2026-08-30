"""
Unit tests for Merchant Identity Resolver (M24).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.merchant_identity import MerchantIdentityResolver


class TestMerchantIdentity(unittest.TestCase):
    """Merchant Identity test suite."""

    def test_01_resolve_registered_merchant(self) -> None:
        """Verify resolution of a registered domain (e.g. bluetokaicoffee.com)."""
        identity = MerchantIdentityResolver.resolve_seller_identity(
            "https://bluetokaicoffee.com/products/attikan-estate"
        )
        self.assertEqual(identity.domain, "bluetokaicoffee.com")
        self.assertEqual(identity.merchant_id, "mer_bluetokai")
        self.assertEqual(identity.identity_status, "VERIFIED")

    def test_02_resolve_unregistered_domain(self) -> None:
        """Verify resolution of an unregistered public domain."""
        identity = MerchantIdentityResolver.resolve_seller_identity(
            "https://unknownstore.in/products/item1"
        )
        self.assertEqual(identity.domain, "unknownstore.in")
        self.assertEqual(identity.identity_status, "SOURCE_BACKED")

    def test_03_resolve_empty_url(self) -> None:
        """Verify resolution of empty URL returns UNKNOWN identity."""
        identity = MerchantIdentityResolver.resolve_seller_identity("")
        self.assertEqual(identity.domain, "unknown.local")
        self.assertEqual(identity.identity_status, "UNKNOWN")
