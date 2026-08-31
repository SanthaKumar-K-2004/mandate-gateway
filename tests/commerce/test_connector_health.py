"""
Unit tests for Commerce Connector Health Monitoring (M25).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.connector_health import CommerceConnectorHealthMonitor


class TestConnectorHealth(unittest.TestCase):
    """CommerceConnectorHealthMonitor test suite."""

    def test_01_initial_health_metrics(self) -> None:
        """Verify initial health metrics for registered connectors."""
        monitor = CommerceConnectorHealthMonitor()
        metrics = monitor.get_health_metrics()

        self.assertEqual(metrics["status"], "SUCCESS")
        self.assertIn("connector_cafe_acme_api", metrics["connectors"])
        self.assertIn("connector_generic_web", metrics["connectors"])

        acme = metrics["connectors"]["connector_cafe_acme_api"]
        self.assertEqual(acme["status"], "HEALTHY")
        self.assertEqual(acme["latency_ms"], 210)

    def test_02_record_call_latency_and_degradation(self) -> None:
        """Verify recording calls updates latency and status upon high error rate."""
        monitor = CommerceConnectorHealthMonitor()

        # Record multiple failed calls to trigger DEGRADED status
        for _ in range(10):
            monitor.record_call("connector_test_api", duration_ms=500.0, is_success=False)

        metrics = monitor.get_health_metrics()
        test_conn = metrics["connectors"]["connector_test_api"]
        self.assertIn(test_conn["status"], ("DEGRADED", "UNAVAILABLE"))
