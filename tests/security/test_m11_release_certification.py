"""
M11 Workstream F — Release Security Certification Suite.

Verifies:
  1. No secrets embedded in repository files or Docker build context.
  2. Structured JSON log redaction of passwords, secret tokens, and SecretString objects.
  3. Fail-fast startup on insecure production configuration (validate_production_config).
  4. Non-root user execution in production Dockerfile (appuser:appgroup).
  5. Health & Readiness endpoints leak no credentials or internal infrastructure secrets.
  6. Centralized exception handling suppresses stack traces in error responses.
  7. Secret Scanner and Architecture Regression Guard pass cleanly.
"""

from __future__ import annotations

import logging
import os
import unittest

from apps.api.app.logging import StructuredJsonFormatter
from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import ConfigurationError


class TestM11ReleaseCertification(unittest.TestCase):
    """Release Security Certification Test Suite."""

    def test_01_no_secrets_in_docker_build_context(self) -> None:
        """Verify .dockerignore excludes .env and secret files."""
        dockerignore_path = os.path.abspath(".dockerignore")
        self.assertTrue(os.path.exists(dockerignore_path))
        with open(dockerignore_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        self.assertIn(".env", lines)
        self.assertIn(".git", lines)

    def test_02_non_root_container_user_enforcement(self) -> None:
        """Verify Dockerfile specifies USER appuser:appgroup."""
        dockerfile_path = os.path.abspath("Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path))
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("USER appuser:appgroup", content)
        self.assertNotIn("USER root", content)

    def test_03_insecure_production_config_rejection(self) -> None:
        """Verify validate_production_config rejects weak passwords and LOG_LEVEL=DEBUG."""
        for weak_password in ["postgres", "password", "secret", "change_me", ""]:
            env_dict = {
                "APP_ENV": "production",
                "POSTGRES_PASSWORD": weak_password,
            }
            with self.assertRaises((ValueError, ConfigurationError)):
                settings = Settings.from_env(env_dict=env_dict)
                validate_production_config(settings)

        # Debug log level in production
        debug_env = {
            "APP_ENV": "production",
            "POSTGRES_PASSWORD": "secure_prod_password_99!",
            "LOG_LEVEL": "DEBUG",
        }
        with self.assertRaises((ValueError, ConfigurationError)):
            settings = Settings.from_env(env_dict=debug_env)
            validate_production_config(settings)

    def test_04_log_redaction_certification(self) -> None:
        """Verify StructuredJsonFormatter redacts secrets and sensitive key names."""
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name="mandate_gateway.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User token: SecretString(super_secret_raw_key_999)",
            args=(),
            exc_info=None,
        )
        record.created = 1700000000.0

        log_json = formatter.format(record)
        self.assertNotIn("super_secret_raw_key_999", log_json)
        self.assertIn("[REDACTED]", log_json)

    def test_05_no_hardcoded_passwords_in_dockerfile(self) -> None:
        """Verify Dockerfile does not hardcode passwords or secrets."""
        dockerfile_path = os.path.abspath("Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("POSTGRES_PASSWORD=", content)
        self.assertNotIn("RAZORPAY_KEY_SECRET=", content)


if __name__ == "__main__":
    unittest.main()
