"""
Unit tests for Commerce Connector Registry & Resolver (M24).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.connector_registry import CommerceConnectorRegistry
from apps.api.commerce.connector_resolver import CheckoutCapabilityResolver
from apps.api.commerce.connectors.base import CommerceConnector, CommerceConnectorError
from apps.api.commerce.connectors.generic_web import GenericWebCheckoutConnector
from apps.api.commerce.models import (
    CheckoutCapability,
    CommerceConnectorResult,
    ConnectorEnvironment,
    VerifiedProduct,
)
from apps.api.commerce.product_truth_engine import ProductTruthEngine


class MockApiConnector(CommerceConnector):
    @property
    def connector_id(self) -> str:
        return "connector_cafe_acme_api"

    @property
    def capability(self) -> CheckoutCapability:
        return CheckoutCapability.VERIFIED_API

    @property
    def environment(self) -> ConnectorEnvironment:
        return ConnectorEnvironment.SANDBOX

    def supports_domain(self, domain: str) -> bool:
        return domain == "cafeacme.local"

    def revalidate_product(self, product: VerifiedProduct) -> CommerceConnectorResult:
        return CommerceConnectorResult(self.connector_id, self.capability, "SUCCESS", "Valid")

    def prepare_checkout(
        self, request_id: str, product: VerifiedProduct, buyer_id: str
    ) -> CommerceConnectorResult:
        return CommerceConnectorResult(self.connector_id, self.capability, "SUCCESS", "Prepared")

    def verify_order(self, order_id: str, payment_transaction_id: str) -> CommerceConnectorResult:
        return CommerceConnectorResult(self.connector_id, self.capability, "SUCCESS", "Verified")


class TestConnectorRegistry(unittest.TestCase):
    """Connector Registry test suite."""

    def test_01_registry_fallback_to_generic_web(self) -> None:
        """Verify unregistered domain resolves to GenericWebCheckoutConnector."""
        registry = CommerceConnectorRegistry()
        conn = registry.resolve_connector("randomstore.com")
        self.assertIsInstance(conn, GenericWebCheckoutConnector)
        self.assertEqual(conn.capability, CheckoutCapability.CHECKOUT_HANDOFF)

    def test_02_register_and_resolve_api_connector(self) -> None:
        """Verify registered domain resolves to specific API connector."""
        registry = CommerceConnectorRegistry()
        api_conn = MockApiConnector()
        registry.register_connector(api_conn, target_domains=["cafeacme.local"])

        resolved = registry.resolve_connector("cafeacme.local")
        self.assertEqual(resolved.connector_id, "connector_cafe_acme_api")
        self.assertEqual(resolved.capability, CheckoutCapability.VERIFIED_API)

    def test_03_duplicate_registration_rejected(self) -> None:
        """Verify duplicate connector registration is rejected."""
        registry = CommerceConnectorRegistry()
        api_conn = MockApiConnector()
        registry.register_connector(api_conn, target_domains=["cafeacme.local"])

        with self.assertRaises(CommerceConnectorError):
            registry.register_connector(api_conn)

    def test_04_resolver_capability_bounds(self) -> None:
        """
        Verify capability resolver assigns VERIFIED_API to integrated domain
        and CHECKOUT_HANDOFF to generic domain.
        """
        registry = CommerceConnectorRegistry()
        api_conn = MockApiConnector()
        registry.register_connector(api_conn, target_domains=["cafeacme.local"])

        resolver = CheckoutCapabilityResolver(registry)

        # Integrated store
        truth1 = ProductTruthEngine.evaluate_product(
            {
                "name": "Tea",
                "source_url": "https://cafeacme.local/p/tea.html",
                "amount_paise": 14000,
            }
        )
        cap1, msg1 = resolver.resolve_capability(truth1.product)
        self.assertEqual(cap1, CheckoutCapability.VERIFIED_API)

        # Generic store
        truth2 = ProductTruthEngine.evaluate_product(
            {
                "name": "Coffee",
                "source_url": "https://bluetokaicoffee.com/products/attikan-estate",
                "amount_paise": 48000,
            }
        )
        cap2, msg2 = resolver.resolve_capability(truth2.product)
        self.assertEqual(cap2, CheckoutCapability.CHECKOUT_HANDOFF)
