"""
M20 Dashboard API Integration Suite
===================================
Workstreams 1, 3 & 12 — Verifies dashboard HTML endpoint rendering,
operational metrics calculation, and typed API response structures.
"""

from __future__ import annotations

import unittest
from apps.api.app.factory import create_fastapi_app
from apps.api.app.ui_dashboard import get_dashboard_html


class TestM20DashboardAPIIntegration(unittest.TestCase):
    """Dashboard API integration test suite."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        if not self.app:
            self.skipTest("FastAPI not installed")
        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    def test_01_dashboard_html_rendering(self) -> None:
        """Verify get_dashboard_html returns valid HTML5 document."""
        html = get_dashboard_html()
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("RAZERPAY", html)
        self.assertIn("Merchant Operations Dashboard", html)

    def test_02_dashboard_ui_endpoint(self) -> None:
        """Verify GET /ui endpoint serves dashboard HTML."""
        res = self.client.get("/ui")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))

    def test_03_operations_summary_endpoint(self) -> None:
        """Verify GET /internal/operations/summary returns metrics JSON."""
        headers = {
            "Authorization": "Bearer rzp_live_operator_token_123",
            "X-Operator-Token": "rzp_live_operator_token_123",
        }
        res = self.client.get("/internal/operations/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertIn(data["status"], ("SECURE", "OPERATIONAL", "HEALTHY"))


if __name__ == "__main__":
    unittest.main()
