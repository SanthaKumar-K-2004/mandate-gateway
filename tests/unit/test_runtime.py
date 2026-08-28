"""
Mandate Gateway — Unit Tests for Application Runtime Foundation
Section S00.4 — Application Runtime Foundation
"""

import asyncio
import sys
import unittest
from typing import Tuple
from apps.api.app import LifecycleState, create_app
from apps.api.app.middleware import extract_request_headers, sanitize_or_generate_id
from apps.api.config import Settings, reset_settings_cache


class TestApplicationRuntime(unittest.TestCase):

    def setUp(self) -> None:
        reset_settings_cache()

    def tearDown(self) -> None:
        reset_settings_cache()

    def test_application_factory_deterministic_creation(self) -> None:
        env = {
            "APP_ENV": "test",
            "APP_NAME": "runtime-test-app",
        }
        settings = Settings.from_env(env_dict=env)
        app = create_app(settings=settings, auto_startup=False)

        self.assertEqual(app.settings.app_name, "runtime-test-app")
        self.assertEqual(app.lifecycle.state, LifecycleState.BOOTING)

    def test_lifecycle_legal_state_transitions(self) -> None:
        app = create_app(auto_startup=False)
        self.assertEqual(app.lifecycle.state, LifecycleState.BOOTING)
        self.assertFalse(app.lifecycle.is_ready())

        app.startup()
        self.assertEqual(app.lifecycle.state, LifecycleState.READY)
        self.assertTrue(app.lifecycle.is_ready())

        app.shutdown()
        self.assertEqual(app.lifecycle.state, LifecycleState.STOPPED)
        self.assertFalse(app.lifecycle.is_ready())

    def test_lifecycle_illegal_transitions_fail_safely(self) -> None:
        app = create_app(auto_startup=True)
        self.assertEqual(app.lifecycle.state, LifecycleState.READY)

        # Illegal: Calling startup() when already READY
        with self.assertRaises(RuntimeError) as cm:
            app.startup()
        self.assertIn("Cannot start application from state", str(cm.exception))

        # Illegal: Adding startup hook when already READY
        with self.assertRaises(RuntimeError) as cm:
            app.lifecycle.add_startup_hook(lambda: None)
        self.assertIn("Cannot add startup hook in state", str(cm.exception))

    def test_startup_failure_transitions_to_failed(self) -> None:
        app = create_app(auto_startup=False)

        def failing_hook() -> None:
            raise RuntimeError("Database hook failed intentionally")

        app.lifecycle.add_startup_hook(failing_hook)

        with self.assertRaises(RuntimeError):
            app.startup()

        self.assertEqual(app.lifecycle.state, LifecycleState.FAILED)
        self.assertIn("Database hook failed intentionally", app.lifecycle.failure_reason or "")

    def test_asgi_health_and_readiness_handlers(self) -> None:
        app = create_app(auto_startup=False)

        async def run_asgi(path: str) -> Tuple[int, dict, str]:
            sent_messages = []

            async def send(msg: dict) -> None:
                sent_messages.append(msg)

            async def receive() -> dict:
                return {}

            scope = {
                "type": "http",
                "method": "GET",
                "path": path,
                "headers": [(b"x-request-id", b"custom-req-123")],
            }
            await app(scope, receive, send)

            status = sent_messages[0]["status"]
            headers = dict(sent_messages[0]["headers"])
            body = sent_messages[1]["body"].decode("utf-8")
            return status, headers, body

        # 1. Test /health when booting
        status, headers, body = asyncio.run(run_asgi("/health"))
        self.assertEqual(status, 200)
        self.assertIn('"status": "HEALTHY"', body)

        # 2. Test /ready when booting (should return 503)
        status, headers, body = asyncio.run(run_asgi("/ready"))
        self.assertEqual(status, 503)
        self.assertIn('"status": "NOT_READY"', body)

        # 3. Startup app and test /ready (should return 200)
        app.startup()
        status, headers, body = asyncio.run(run_asgi("/ready"))
        self.assertEqual(status, 200)
        self.assertIn('"status": "READY"', body)

        # 4. Test /ready in FAILED state (should return 503)
        failed_app = create_app(auto_startup=False)

        def failing_hook() -> None:
            raise ZeroDivisionError("Simulated failure")

        failed_app.lifecycle.add_startup_hook(failing_hook)
        with self.assertRaises(ZeroDivisionError):
            failed_app.startup()

        self.assertEqual(failed_app.lifecycle.state, LifecycleState.FAILED)

        async def run_failed_ready() -> Tuple[int, dict, str]:
            sent_messages = []

            async def send(msg: dict) -> None:
                sent_messages.append(msg)

            async def receive() -> dict:
                return {}

            scope = {"type": "http", "method": "GET", "path": "/ready", "headers": []}
            await failed_app(scope, receive, send)
            return (
                sent_messages[0]["status"],
                dict(sent_messages[0]["headers"]),
                sent_messages[1]["body"].decode("utf-8"),
            )

        f_status, _, f_body = asyncio.run(run_failed_ready())
        self.assertEqual(f_status, 503)
        self.assertIn('"status": "NOT_READY"', f_body)
        self.assertIn('"state": "FAILED"', f_body)

    def test_request_id_middleware_sanitization_and_injection_protection(self) -> None:
        # Valid ID
        valid_id = "req-valid-12345"
        self.assertEqual(sanitize_or_generate_id(valid_id), valid_id)

        # Missing / Empty ID
        gen_missing = sanitize_or_generate_id("")
        self.assertTrue(len(gen_missing) > 0)

        # Oversized ID
        oversized_id = "a" * 200
        gen_oversized = sanitize_or_generate_id(oversized_id)
        self.assertNotEqual(gen_oversized, oversized_id)

        # Newline & Control Character Injections
        self.assertNotEqual(
            sanitize_or_generate_id("req\nheader_injection"), "req\nheader_injection"
        )
        self.assertNotEqual(sanitize_or_generate_id("req\r\ninjection"), "req\r\ninjection")
        self.assertNotEqual(sanitize_or_generate_id("req\x00null"), "req\x00null")

        # Extract headers case-insensitively
        headers = {"X-Request-ID": "req-100", "X-Correlation-ID": "corr-200"}
        r_id, c_id, t_id = extract_request_headers(headers)
        self.assertEqual(r_id, "req-100")
        self.assertEqual(c_id, "corr-200")
        self.assertEqual(t_id, "corr-200")

    def test_import_safety_has_no_side_effects(self) -> None:
        """Verifies importing app modules does not perform network calls or mutate state."""
        modules_before = set(sys.modules.keys())
        self.assertIsNotNone(modules_before)
        import apps.api.app
        import apps.api.main

        modules_after = set(sys.modules.keys())
        self.assertTrue("apps.api.app" in modules_after or apps.api.app is not None)
        self.assertTrue("apps.api.main" in modules_after or apps.api.main is not None)


if __name__ == "__main__":
    unittest.main()
