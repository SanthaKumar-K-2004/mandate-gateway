"""
Unit tests for Production Hardening & Network Safety (M26).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.network_client import (
    CircuitBreakerOpenError,
    ResilientCommerceNetworkClient,
)


class TestM26ProductionHardening(unittest.TestCase):
    """ResilientCommerceNetworkClient test suite."""

    def test_01_successful_request_execution(self) -> None:
        """Verify successful request execution clears circuit breaker state."""
        client = ResilientCommerceNetworkClient()
        success, resp, msg = client.execute_request(
            connector_id="connector_test_01",
            method="GET",
            url="https://world.openfoodfacts.org/api/v1/product/1.json",
            is_idempotent=True,
        )

        self.assertTrue(success)
        self.assertEqual(msg, "SUCCESS")
        self.assertEqual(client.get_circuit_state("connector_test_01"), "HEALTHY")

    def test_02_production_https_enforcement(self) -> None:
        """Verify production environment rejects non-HTTPS target URLs."""
        client = ResilientCommerceNetworkClient(app_env="production")
        success, resp, msg = client.execute_request(
            connector_id="connector_test_02",
            method="GET",
            url="http://insecure.merchant.com/api",
            is_idempotent=True,
        )

        self.assertFalse(success)
        self.assertEqual(msg, "HTTPS_REQUIRED")

    def test_03_circuit_breaker_tripping(self) -> None:
        """Verify circuit breaker trips to CIRCUIT_OPEN after max failure threshold."""
        client = ResilientCommerceNetworkClient(max_failure_threshold=3, circuit_cooldown_s=10.0)

        # Trigger 3 failures
        for _ in range(3):
            client._record_failure("connector_test_trip")

        self.assertEqual(client.get_circuit_state("connector_test_trip"), "CIRCUIT_OPEN")

        with self.assertRaises(CircuitBreakerOpenError):
            client.execute_request(
                connector_id="connector_test_trip",
                method="GET",
                url="https://api.test.com",
                is_idempotent=True,
            )
