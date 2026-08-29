"""
Security Verification Tests for M09 — Production Container Security, Configuration Hardening, & Fail-Closed Behavior.

Verifies:
  1. Dockerfile specifies non-root user execution (USER appuser:appgroup).
  2. .dockerignore excludes sensitive environment files and secrets.
  3. Production settings fail fast on default/insecure database passwords.
  4. Readiness probe degrades to HTTP 503 NOT_READY when PostgreSQL or Redis dependencies fail in production mode.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.app.health import handle_ready_async
from apps.api.app.lifecycle import AppLifecycle
from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import ConfigurationError


class TestM09ProductionSecurity(unittest.IsolatedAsyncioTestCase):
    """Production security verification test suite."""

    def test_dockerfile_non_root_user_security(self) -> None:
        """Verify Dockerfile enforces non-root user execution."""
        dockerfile_path = os.path.abspath("Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path))

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("useradd", content)
        self.assertIn("USER appuser:appgroup", content)
        self.assertNotIn("USER root", content)

    def test_dockerignore_secret_exclusion_hygiene(self) -> None:
        """Verify .dockerignore excludes .env and sensitive environment files."""
        dockerignore_path = os.path.abspath(".dockerignore")
        self.assertTrue(os.path.exists(dockerignore_path))

        with open(dockerignore_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        self.assertIn(".env", lines)
        self.assertIn(".git", lines)

    def test_fail_fast_production_config_validation(self) -> None:
        """Verify validate_production_config rejects insecure default passwords in production."""
        for bad_pass in ["postgres", "password", "secret", "change_me", ""]:
            env_dict = {
                "APP_ENV": "production",
                "POSTGRES_PASSWORD": bad_pass,
            }
            with self.assertRaises(
                (ValueError, ConfigurationError), msg=f"Should reject password '{bad_pass}'"
            ):
                settings = Settings.from_env(env_dict=env_dict)
                validate_production_config(settings)

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_readiness_degradation_when_db_down_in_production(
        self, mock_redis_health: AsyncMock, mock_db_health: AsyncMock
    ) -> None:
        """Verify /ready returns 503 NOT_READY when database health check fails in production mode."""
        mock_db_health.return_value = {"status": "UNAVAILABLE", "connected": False}
        mock_redis_health.return_value = {"status": "CONNECTED", "connected": True}

        env_dict = {
            "APP_ENV": "production",
            "POSTGRES_PASSWORD": "secure_prod_password_123!#",
        }
        prod_settings = Settings.from_env(env_dict=env_dict)
        lifecycle = AppLifecycle()
        lifecycle.startup()

        status_code, body = await handle_ready_async(lifecycle, prod_settings)
        self.assertEqual(status_code, 503)
        self.assertEqual(body["status"], "NOT_READY")
        self.assertEqual(body["dependencies"]["database"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
