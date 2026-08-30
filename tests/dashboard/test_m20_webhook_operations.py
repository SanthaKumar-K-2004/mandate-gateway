"""
M20 Webhook Operations Center Suite
====================================
Workstream 8 — Verifies webhook subscription creation, listing, status updates,
and delivery log visibility in the dashboard.
"""

from __future__ import annotations

import unittest
from apps.api.app.factory import create_fastapi_app


class TestM20WebhookOperations(unittest.TestCase):
    """Webhook operations test suite."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        if not self.app:
            self.skipTest("FastAPI not installed")
        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    def test_01_create_and_list_subscriptions(self) -> None:
        """Verify registering a new webhook subscription via dashboard API."""
        payload = {
            "merchant_id": "mer_dashboard_01",
            "url": "https://dashboard.merchant.com/webhooks",
            "events": ["payment.captured"],
            "secret": "whsec_dash_secret_123",
        }
        res = self.client.post("/api/webhooks/subscriptions", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("subscription_id", data)
        sub_id = data["subscription_id"]

        # List subscriptions
        res_list = self.client.get("/api/webhooks/subscriptions?merchant_id=mer_dashboard_01")
        self.assertEqual(res_list.status_code, 200)
        self.assertGreaterEqual(res_list.json()["count"], 1)

        # Update status
        res_patch = self.client.patch(
            f"/api/webhooks/subscriptions/{sub_id}",
            json={"status": "DISABLED"},
        )
        self.assertEqual(res_patch.status_code, 200)
        self.assertEqual(res_patch.json()["status"], "DISABLED")

    def test_02_view_deliveries(self) -> None:
        """Verify delivery log endpoint returns delivery history."""
        res = self.client.get("/api/webhooks/deliveries")
        self.assertEqual(res.status_code, 200)
        self.assertIn("deliveries", res.json())


if __name__ == "__main__":
    unittest.main()
