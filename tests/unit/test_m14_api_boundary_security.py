"""
M14 Unit Tests — API Boundary Security, Request Size Guard, Headers Sanitization & Error Contract
"""

import unittest

from apps.api.app.factory import create_fastapi_app
from fastapi.testclient import TestClient


class TestM14ApiBoundarySecurity(unittest.TestCase):
    """Test request body size limit, header sanitization, enumeration resistance, and error contract."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        self.client = TestClient(self.app)

    def test_enumeration_resistant_auth_response(self) -> None:
        # Invalid key format
        r1 = self.client.get(
            "/api/merchants/mer_123", headers={"Authorization": "Bearer invalid_key"}
        )
        self.assertEqual(r1.status_code, 401)
        data1 = r1.json()
        self.assertIn("error", data1)
        self.assertEqual(data1["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(data1["error"]["message"], "Invalid API authentication credentials.")

        # Missing header
        r2 = self.client.get("/api/merchants/mer_123")
        self.assertEqual(r2.status_code, 401)
        data2 = r2.json()
        self.assertEqual(data2["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(data2["error"]["message"], "Invalid API authentication credentials.")

    def test_oversized_payload_rejection(self) -> None:
        # Send payload > 1MB (1,048,576 bytes)
        large_body = "x" * (1024 * 1024 + 100)
        r = self.client.post(
            "/api/merchants",
            content=large_body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(large_body)),
            },
        )
        self.assertEqual(r.status_code, 413)
        data = r.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "PAYLOAD_TOO_LARGE")

    def test_operator_endpoint_requires_operator_credentials(self) -> None:
        # Unauthenticated internal operations call
        r1 = self.client.get("/internal/operations/alerts")
        self.assertEqual(r1.status_code, 401)

        # Authenticated with valid operator token
        r2 = self.client.get(
            "/internal/operations/alerts",
            headers={"X-Operator-Token": "rzp_live_operator_token_123"},
        )
        self.assertEqual(r2.status_code, 200)
        data2 = r2.json()
        self.assertIn("alerts_count", data2)

    def test_public_health_probes(self) -> None:
        r1 = self.client.get("/health/live")
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.get("/health/ready")
        self.assertIn(r2.status_code, (200, 503))


if __name__ == "__main__":
    unittest.main()
