"""
M21 Environment Configuration Test Suite
========================================
Workstream 2 — Verifies environment classification (development, staging, production),
production fail-closed configuration validation, and cross-environment isolation guards.
"""

from __future__ import annotations

import unittest
from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import ConfigurationError, Environment


class TestM21EnvironmentConfig(unittest.TestCase):
    """Environment configuration and validation test suite."""

    def test_01_development_environment_defaults(self) -> None:
        """Verify development configuration loads cleanly with default settings."""
        env = {
            "APP_ENV": "development",
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PASSWORD": "CHANGE_ME_LOCAL_ONLY",
        }
        settings = Settings.from_env(env_dict=env, host_context=True)
        self.assertEqual(settings.app_env, Environment.DEVELOPMENT)
        self.assertEqual(settings.postgres_host, "127.0.0.1")
        self.assertFalse(settings.demo_mode)

    def test_02_staging_environment(self) -> None:
        """Verify staging configuration loads with explicit staging parameters."""
        env = {
            "APP_ENV": "staging",
            "POSTGRES_HOST": "db.staging.internal",
            "POSTGRES_PASSWORD": "staging_secure_password_981",
            "REDIS_HOST": "redis.staging.internal",
            "DEMO_MODE": "true",
        }
        settings = Settings.from_env(env_dict=env, host_context=True)
        self.assertEqual(settings.app_env, Environment.STAGING)
        self.assertTrue(settings.demo_mode)

    def test_03_production_valid_configuration(self) -> None:
        """Verify production configuration validates cleanly when all secure secrets are provided."""
        env = {
            "APP_ENV": "production",
            "POSTGRES_HOST": "db.prod.internal",
            "POSTGRES_PASSWORD": "super_secure_prod_password_98127391823",
            "REDIS_HOST": "cache.prod.internal",
            "LOG_LEVEL": "INFO",
        }
        settings = Settings.from_env(env_dict=env, host_context=True)
        self.assertEqual(settings.app_env, Environment.PRODUCTION)
        # Should not raise ConfigurationError
        validate_production_config(settings)

    def test_04_production_rejects_insecure_password(self) -> None:
        """Verify production configuration fails closed when POSTGRES_PASSWORD is default or weak."""
        env = {
            "APP_ENV": "production",
            "POSTGRES_HOST": "db.prod.internal",
            "POSTGRES_PASSWORD": "postgres",
        }
        with self.assertRaises(ConfigurationError):
            settings = Settings.from_env(env_dict=env, host_context=True)
            validate_production_config(settings)

    def test_05_production_rejects_debug_log_level(self) -> None:
        """Verify production configuration fails closed if LOG_LEVEL is DEBUG."""
        env = {
            "APP_ENV": "production",
            "POSTGRES_HOST": "db.prod.internal",
            "POSTGRES_PASSWORD": "super_secure_prod_password_98127391823",
            "LOG_LEVEL": "DEBUG",
        }
        settings = Settings.from_env(env_dict=env, host_context=True)
        with self.assertRaises(ConfigurationError):
            validate_production_config(settings)

    def test_06_container_boundary_localhost_rejection(self) -> None:
        """Verify container environment rejects localhost database host."""
        env = {
            "APP_ENV": "production",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PASSWORD": "super_secure_prod_password_98127391823",
        }
        with self.assertRaises(ConfigurationError):
            Settings.from_env(env_dict=env, host_context=False)


if __name__ == "__main__":
    unittest.main()
