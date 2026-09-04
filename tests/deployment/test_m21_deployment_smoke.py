"""
M21 Deployment Smoke Test Suite
===============================
Workstream 6 — Validates application startup, health & readiness endpoints,
API route acceptance, and dependency status reporting.
"""

from __future__ import annotations

import unittest
from apps.api.app.factory import create_fastapi_app


class TestM21DeploymentSmoke(unittest.TestCase):
    """Deployment smoke test suite."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        if not self.app:
            self.skipTest("FastAPI not installed")
        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    def test_01_health_endpoint(self) -> None:
        """Verify GET /health returns HTTP 200 with healthy status."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertIn(data["status"], ("HEALTHY", "SECURE", "OPERATIONAL"))

    def test_02_ui_dashboard_smoke(self) -> None:
        """Verify GET /ui serves HTML operations dashboard."""
        res = self.client.get("/ui")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertIn("RAZORPAY", res.text)

    def test_03_operations_summary_smoke(self) -> None:
        """Verify GET /internal/operations/summary accepts operator traffic."""
        headers = {
            "Authorization": "Bearer rzp_live_operator_token_123",
            "X-Operator-Token": "rzp_live_operator_token_123",
        }
        res = self.client.get("/internal/operations/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)


if __name__ == "__main__":
    unittest.main()
