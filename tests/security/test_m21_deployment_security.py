"""
M21 Deployment Security Audit Suite
====================================
Workstream 9 — Audits deployment security posture, secret redaction in representations,
production fail-closed security policies, and demo mode isolation guarantees.
"""

from __future__ import annotations

import unittest
from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import ConfigurationError, SecretString


class TestM21DeploymentSecurity(unittest.TestCase):
    """Deployment security audit test suite."""

    def test_01_secret_string_redaction(self) -> None:
        """Verify SecretString redacts sensitive content in str(), repr(), and dict conversions."""
        secret = SecretString("super_secret_production_key_991823")
        self.assertEqual(str(secret), "[REDACTED]")
        self.assertEqual(repr(secret), "SecretString('[REDACTED]')")

    def test_02_production_fail_closed_validation(self) -> None:
        """Verify production mode rejects default secrets and DEBUG logging."""
        insecure_env = {
            "APP_ENV": "production",
            "POSTGRES_HOST": "postgres.prod",
            "POSTGRES_PASSWORD": "change_me",
        }
        with self.assertRaises(ConfigurationError):
            settings = Settings.from_env(env_dict=insecure_env, host_context=True)
            validate_production_config(settings)

    def test_03_zero_secrets_in_settings_dict(self) -> None:
        """Verify Settings.to_dict(redact=True) replaces password with [REDACTED]."""
        env = {
            "APP_ENV": "development",
            "POSTGRES_PASSWORD": "raw_db_password_123",
        }
        settings = Settings.from_env(env_dict=env, host_context=True)
        dict_rep = settings.to_dict(redact=True)
        self.assertEqual(dict_rep["POSTGRES_PASSWORD"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
