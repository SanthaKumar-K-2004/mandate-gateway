"""
M13 — Integration Test Suite for Health, Readiness & Dependency Probes
Section 14 — Test Architecture
"""

import dataclasses
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.app.health import (
    handle_dependencies_async,
    handle_health,
    handle_ready_async,
)
from apps.api.app.lifecycle import AppLifecycle
from apps.api.config.helpers import get_settings
from apps.api.config.types import Environment


class TestM13IntegrationHealthReadiness(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for application health, liveness, readiness, and dependencies."""

    def setUp(self) -> None:
        self.settings = get_settings()
        self.lifecycle = AppLifecycle()

    def test_liveness_probe_handle_health(self) -> None:
        """Verify liveness probe returns 200 OK instantly with process details."""
        status_code, body = handle_health(self.settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["status"], "HEALTHY")
        self.assertEqual(body["service"], self.settings.app_name)

    async def test_readiness_probe_dev_mode(self) -> None:
        """Verify readiness probe returns 200 OK in development mode when lifecycle is READY."""
        self.lifecycle.startup()
        status_code, body = await handle_ready_async(self.lifecycle, self.settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["status"], "READY")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_readiness_probe_prod_mode_fails_on_db_down(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        """Verify readiness probe returns 503 in Production mode when PostgreSQL is unavailable (S06)."""
        prod_settings = dataclasses.replace(get_settings(), app_env=Environment.PRODUCTION)
        self.lifecycle.startup()

        # Database failure scenario
        mock_db.return_value = {"status": "DISCONNECTED", "error": "Connection refused"}
        mock_redis.return_value = {"status": "CONNECTED"}

        status_code, body = await handle_ready_async(self.lifecycle, prod_settings)
        self.assertEqual(status_code, 503)
        self.assertEqual(body["status"], "NOT_READY")
        self.assertEqual(body["dependencies"]["database"], "DISCONNECTED")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_dependency_diagnostics_probe(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        """Verify GET /health/dependencies returns structured subsystem status without exposing credentials."""
        mock_db.return_value = {"status": "CONNECTED"}
        mock_redis.return_value = {"status": "CONNECTED"}

        status_code, body = await handle_dependencies_async(self.settings)
        self.assertEqual(status_code, 200)
        self.assertEqual(body["status"], "healthy")
        self.assertIn("database", body["dependencies"])
        self.assertIn("redis", body["dependencies"])
        self.assertIn("provider", body["dependencies"])
        self.assertIn("outbox", body["dependencies"])
        self.assertIn("recovery", body["dependencies"])


if __name__ == "__main__":
    unittest.main()
