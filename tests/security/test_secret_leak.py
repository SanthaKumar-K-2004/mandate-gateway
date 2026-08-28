"""
Mandate Gateway — Security Tests for Secret Redaction & Leak Prevention
Section S00.3 — Configuration & Secrets Management
"""

import io
import logging
import traceback
import unittest
from apps.api.config import (
    ConfigurationError,
    SecretString,
    Settings,
    config_check_summary,
    reset_settings_cache,
)


class TestSecretLeakPrevention(unittest.TestCase):

    SENTINEL = "TEST_SECRET_SENTINEL_DO_NOT_LEAK_987654321"

    def setUp(self) -> None:
        reset_settings_cache()

    def tearDown(self) -> None:
        reset_settings_cache()

    def test_sentinel_secret_never_appears_in_str_or_repr(self) -> None:
        secret = SecretString(self.SENTINEL)

        self.assertNotIn(self.SENTINEL, str(secret))
        self.assertNotIn(self.SENTINEL, repr(secret))
        self.assertEqual(str(secret), "[REDACTED]")
        self.assertEqual(repr(secret), "SecretString('[REDACTED]')")

    def test_sentinel_secret_never_appears_in_settings_dict_or_repr(self) -> None:
        env = {
            "POSTGRES_PASSWORD": self.SENTINEL,
        }
        settings = Settings.from_env(env_dict=env)

        # 1. Check to_dict(redact=True)
        dict_rep = settings.to_dict(redact=True)
        self.assertNotIn(self.SENTINEL, str(dict_rep))
        self.assertEqual(dict_rep["POSTGRES_PASSWORD"], "[REDACTED]")

        # 2. Check __repr__()
        repr_output = repr(settings)
        self.assertNotIn(self.SENTINEL, repr_output)
        self.assertIn("[REDACTED]", repr_output)

        # 3. Check __str__()
        str_output = str(settings)
        self.assertNotIn(self.SENTINEL, str_output)
        self.assertIn("[REDACTED]", str_output)

    def test_sentinel_secret_never_appears_in_config_check_summary(self) -> None:
        env = {
            "POSTGRES_PASSWORD": self.SENTINEL,
        }
        settings = Settings.from_env(env_dict=env)
        summary = config_check_summary(settings)

        self.assertNotIn(self.SENTINEL, summary)
        self.assertIn("PostgreSQL Password      : [REDACTED]", summary)

    def test_logging_settings_does_not_leak_sentinel_secret(self) -> None:
        env = {
            "POSTGRES_PASSWORD": self.SENTINEL,
        }
        settings = Settings.from_env(env_dict=env)

        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger("security_test_logger")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        logger.info("Current configuration: %s", settings)
        logger.info("Config dict: %s", settings.to_dict(redact=True))
        handler.flush()

        log_contents = log_capture.getvalue()
        self.assertNotIn(self.SENTINEL, log_contents)
        self.assertIn("[REDACTED]", log_contents)

    def test_exception_traceback_does_not_leak_sentinel_secret(self) -> None:
        """Verifies that an exception formatting a SecretString does not leak secrets in tracebacks."""
        env = {
            "POSTGRES_PASSWORD": self.SENTINEL,
        }
        settings = Settings.from_env(env_dict=env)

        try:
            # Format exception carrying settings representation
            raise ConfigurationError(
                f"Configuration failed during startup with settings: {settings}"
            )
        except ConfigurationError as err:
            tb = "".join(traceback.format_exception(err))
            self.assertNotIn(self.SENTINEL, str(err))
            self.assertNotIn(self.SENTINEL, tb)
            self.assertIn("[REDACTED]", str(err))


if __name__ == "__main__":
    unittest.main()
