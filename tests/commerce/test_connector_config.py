"""
Unit tests for Commerce Connector Configuration System (M26).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.connector_config import (
    CommerceConnectorConfigManager,
    ConnectorConfigurationError,
)


class TestConnectorConfig(unittest.TestCase):
    """CommerceConnectorConfigManager test suite."""

    def test_01_load_default_configurations(self) -> None:
        """Verify default development configuration loading and secret redaction."""
        mgr = CommerceConnectorConfigManager(env={"APP_ENV": "development"})
        self.assertTrue(mgr.connectors_enabled)

        safe_dict = mgr.get_all_safe_settings()
        self.assertGreaterEqual(len(safe_dict), 2)

        for s in safe_dict:
            self.assertIn("api_key_masked", s)
            self.assertIn("webhook_secret_masked", s)
            self.assertNotIn("key_cafeacme_live_m26", str(s))

    def test_02_production_rejects_demo_connector(self) -> None:
        """Verify production environment fails closed if DEMO connector is configured as active."""
        env = {
            "APP_ENV": "production",
            "MERCHANT_CONNECTOR_1_ENABLED": "true",
            "MERCHANT_CONNECTOR_1_BASE_URL": "https://api.cafeacme.local",
            "MERCHANT_CONNECTOR_1_ENVIRONMENT": "DEMO",
        }
        with self.assertRaises(ConnectorConfigurationError):
            CommerceConnectorConfigManager(env=env)

    def test_03_production_rejects_http_base_url(self) -> None:
        """Verify production environment fails closed if non-HTTPS base URL is configured."""
        env = {
            "APP_ENV": "production",
            "MERCHANT_CONNECTOR_1_ENABLED": "true",
            "MERCHANT_CONNECTOR_1_BASE_URL": "http://api.insecure.com",
            "MERCHANT_CONNECTOR_1_ENVIRONMENT": "LIVE",
        }
        with self.assertRaises(ConnectorConfigurationError):
            CommerceConnectorConfigManager(env=env)
