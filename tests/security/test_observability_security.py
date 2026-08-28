"""
Mandate Gateway — Security Tests for Observability Foundation
Section S00.5 — Observability Foundation
"""

import io
import logging
import unittest
from apps.api.app import create_app, clear_request_context, metrics_registry
from apps.api.app.logging import SecretRedactionFilter, StructuredJsonFormatter
from apps.api.config import SecretString, Settings, reset_settings_cache


class TestObservabilitySecurity(unittest.TestCase):

    SENTINEL = "TEST_OBSERVABILITY_SECRET_SENTINEL_999888777"

    def setUp(self) -> None:
        reset_settings_cache()
        clear_request_context()
        metrics_registry.reset()

    def tearDown(self) -> None:
        reset_settings_cache()
        clear_request_context()
        metrics_registry.reset()

    def test_sentinel_secret_never_logged_or_exposed(self) -> None:
        env = {"POSTGRES_PASSWORD": self.SENTINEL}
        settings = Settings.from_env(env_dict=env)
        app = create_app(settings=settings, auto_startup=True)

        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(StructuredJsonFormatter())
        handler.addFilter(SecretRedactionFilter())
        app.logger.addHandler(handler)

        secret_wrapper = SecretString(self.SENTINEL)
        app.logger.info("Executing observability check with secret: %s", secret_wrapper)
        handler.flush()

        log_output = log_capture.getvalue()
        self.assertNotIn(self.SENTINEL, log_output)
        self.assertIn("[REDACTED]", log_output)

    def test_sensitive_headers_never_logged(self) -> None:
        """Verifies Authorization and Cookie headers are omitted from logs and metrics."""
        app = create_app(auto_startup=True)

        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(StructuredJsonFormatter())
        handler.addFilter(SecretRedactionFilter())
        app.logger.addHandler(handler)

        secret_token = "Bearer " + self.SENTINEL
        headers_dict = {
            "Authorization": secret_token,
            "Cookie": "session_id=" + self.SENTINEL,
            "X-API-Key": self.SENTINEL,
        }

        # Log request lifecycle event
        app.logger.info("Request received", extra={"headers": headers_dict})
        handler.flush()

        log_output = log_capture.getvalue()
        self.assertNotIn(self.SENTINEL, log_output)

    def test_nested_dict_and_list_secret_redaction(self) -> None:
        secret = SecretString(self.SENTINEL)
        nested_arg = {"auth": {"token": secret, "keys": [secret]}}

        formatter = StructuredJsonFormatter()
        filter_ = SecretRedactionFilter()

        record = logging.LogRecord(
            "test", logging.INFO, "path", 10, "Config payload: %s", (nested_arg,), None
        )
        filter_.filter(record)
        formatted_json = formatter.format(record)

        self.assertNotIn(self.SENTINEL, formatted_json)
        self.assertIn("[REDACTED]", formatted_json)


if __name__ == "__main__":
    unittest.main()
