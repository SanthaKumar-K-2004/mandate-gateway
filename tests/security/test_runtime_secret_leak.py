"""
Mandate Gateway — Security Tests for Application Runtime Secret Protection
Section S00.4 — Application Runtime Foundation
"""

import io
import logging
import unittest
from apps.api.app import create_app
from apps.api.app.errors import RuntimeErrorBase
from apps.api.config import SecretString, Settings, reset_settings_cache


class TestRuntimeSecretLeakPrevention(unittest.TestCase):

    SENTINEL = "TEST_RUNTIME_SECRET_SENTINEL_DO_NOT_LEAK_987654321"

    def setUp(self) -> None:
        reset_settings_cache()

    def tearDown(self) -> None:
        reset_settings_cache()

    def test_logger_never_leaks_runtime_sentinel_secret(self) -> None:
        env = {"POSTGRES_PASSWORD": self.SENTINEL}
        settings = Settings.from_env(env_dict=env)
        app = create_app(settings=settings, auto_startup=True)

        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        app.logger.addHandler(handler)

        secret_wrapper = SecretString(self.SENTINEL)
        app.logger.info("Application starting with password: %s", secret_wrapper)
        handler.flush()

        log_output = log_capture.getvalue()
        self.assertNotIn(self.SENTINEL, log_output)
        self.assertIn("[REDACTED]", log_output)

    def test_runtime_error_boundary_never_leaks_sentinel(self) -> None:
        secret = SecretString(self.SENTINEL)
        err = RuntimeErrorBase(f"Initialization failed with secret: {secret}")
        err_dict = err.to_dict()

        self.assertNotIn(self.SENTINEL, str(err_dict))
        self.assertIn("[REDACTED]", str(err_dict))

    def test_health_response_never_leaks_secrets(self) -> None:
        env = {"POSTGRES_PASSWORD": self.SENTINEL}
        settings = Settings.from_env(env_dict=env)
        app = create_app(settings=settings, auto_startup=True)

        from apps.api.app.health import handle_health, handle_ready

        _, health_body = handle_health(app.settings)
        _, ready_body = handle_ready(app.lifecycle, app.settings)

        self.assertNotIn(self.SENTINEL, str(health_body))
        self.assertNotIn(self.SENTINEL, str(ready_body))

    def test_nested_structures_and_repr_redaction(self) -> None:
        """Verifies SecretString redaction when contained within nested dicts, lists, str(), and repr()."""
        secret = SecretString(self.SENTINEL)

        nested_dict = {"credentials": {"db": {"password": secret}}}
        nested_list = [1, "config", secret]

        # Verify str() and repr() outputs redact sentinel
        self.assertNotIn(self.SENTINEL, str(secret))
        self.assertNotIn(self.SENTINEL, repr(secret))

        # Formatted string representations
        str_dict = str(nested_dict)
        str_list = str(nested_list)

        self.assertNotIn(self.SENTINEL, str_dict)
        self.assertNotIn(self.SENTINEL, str_list)
        self.assertIn("[REDACTED]", str_dict)
        self.assertIn("[REDACTED]", str_list)


if __name__ == "__main__":
    unittest.main()
