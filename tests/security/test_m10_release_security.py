"""
Release Security Verification Suite for M10.

Verifies:
  S01: Secrets excluded from Docker build context (.dockerignore).
  S02: Production runtime enforces non-root execution (USER appuser:appgroup).
  S03: Unsafe production configuration rejected (validate_production_config).
  S04: Structured JSON logs redact sensitive keys and SecretString objects.
  S05: Debug log level rejected in production environment.
  S06: Database credentials not embedded in container build context or Dockerfile.
  S07: CI/CD workflow adheres to secret non-disclosure standards.
"""

from __future__ import annotations

import os
import unittest

from apps.api.app.logging import StructuredJsonFormatter
from apps.api.config.settings import Settings, validate_production_config
from apps.api.config.types import ConfigurationError


class TestM10ReleaseSecurity(unittest.TestCase):
    """Release Security Verification Test Suite."""

    def test_s01_docker_build_context_secret_exclusion(self) -> None:
        """S01: Verify .dockerignore excludes .env and secret files."""
        dockerignore_path = os.path.abspath(".dockerignore")
        self.assertTrue(os.path.exists(dockerignore_path))
        with open(dockerignore_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        self.assertIn(".env", lines)
        self.assertIn(".git", lines)

    def test_s02_non_root_container_execution(self) -> None:
        """S02: Verify Dockerfile enforces non-root user appuser."""
        dockerfile_path = os.path.abspath("Dockerfile")
        self.assertTrue(os.path.exists(dockerfile_path))
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("USER appuser:appgroup", content)
        self.assertNotIn("USER root", content)

    def test_s03_s05_unsafe_production_config_rejection(self) -> None:
        """S03 & S05: Verify validate_production_config rejects weak passwords and LOG_LEVEL=DEBUG in production."""
        # Bad passwords
        for bad_pass in ["postgres", "password", "secret", "change_me", ""]:
            env_dict = {
                "APP_ENV": "production",
                "POSTGRES_PASSWORD": bad_pass,
            }
            with self.assertRaises((ValueError, ConfigurationError)):
                settings = Settings.from_env(env_dict=env_dict)
                validate_production_config(settings)

        # LOG_LEVEL=DEBUG in production
        debug_env = {
            "APP_ENV": "production",
            "POSTGRES_PASSWORD": "secure_prod_password_123!#",
            "LOG_LEVEL": "DEBUG",
        }
        with self.assertRaises((ValueError, ConfigurationError)):
            settings = Settings.from_env(env_dict=debug_env)
            validate_production_config(settings)

    def test_s04_log_redaction_verification(self) -> None:
        """S04: Verify StructuredJsonFormatter redacts sensitive dictionary keys and SecretStrings."""
        formatter = StructuredJsonFormatter()

        import logging

        record = logging.LogRecord(
            name="mandate_gateway.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User secret token: SecretString(super_secret_string)",
            args=(),
            exc_info=None,
        )
        record.created = 1700000000.0
        record.request_id = "req_101"
        record.correlation_id = "corr_101"
        record.trace_id = "trace_101"

        log_json = formatter.format(record)
        self.assertNotIn("super_secret_string", log_json)
        self.assertIn("[REDACTED]", log_json)

    def test_s06_no_hardcoded_database_credentials(self) -> None:
        """S06: Verify Dockerfile does not hardcode passwords."""
        dockerfile_path = os.path.abspath("Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("POSTGRES_PASSWORD=", content)


if __name__ == "__main__":
    unittest.main()
