"""
S03.3 — Security Hardening Integration Test Suite.

Tests FastAPI endpoints `/api/security/hardening/status`, `/api/security/rate-limit/check`,
and `/api/security/verify-receipt` (Section 34 & 35, PROJECT_CONTEXT.md).
"""

import unittest
from fastapi.testclient import TestClient

from apps.api.app.factory import create_fastapi_app


class TestHardeningIntegration(unittest.TestCase):
    """Integration test cases for S03.3 Security REST API router."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        self.assertIsNotNone(self.app)
        self.client = TestClient(self.app)

    def test_get_hardening_status_endpoint(self) -> None:
        resp = self.client.get("/api/security/hardening/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["fail_closed_mode_active"])
        self.assertTrue(data["database_persistence_healthy"])
        self.assertTrue(data["rate_limiter_active"])
        self.assertIn("FAIL_CLOSED_AUTHORIZATION_GATEWAY", data["active_threat_mitigations"])

    def test_check_rate_limit_endpoint(self) -> None:
        payload = {
            "identifier": "integration_client_1",
            "action": "test_endpoint",
            "max_requests": 2,
            "window_seconds": 60,
        }

        r1 = self.client.post("/api/security/rate-limit/check", json=payload)
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(r1.json()["allowed"])

        r2 = self.client.post("/api/security/rate-limit/check", json=payload)
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()["allowed"])

        r3 = self.client.post("/api/security/rate-limit/check", json=payload)
        self.assertEqual(r3.status_code, 200)
        self.assertFalse(r3.json()["allowed"])
        self.assertGreater(r3.json()["retry_after_seconds"], 0)

    def test_verify_receipt_endpoint_invalid_signature(self) -> None:
        payload = {
            "receipt_id": "rcpt_test_99",
            "transaction_id": "tx_test_99",
            "mandate_id": "man_test_99",
            "merchant_id": "mer_test_99",
            "policy_version": 1,
            "cart_hash": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "amount_paise": 299900,
            "currency": "INR",
            "decision": "ALLOW",
            "execution_tool": "create_order",
            "execution_reference": "order_9999",
            "audit_hash": "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff",
            "signature": "invalid_hex_signature_payload_for_testing",
        }

        resp = self.client.post("/api/security/verify-receipt", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["valid"])
        self.assertFalse(data["signature_valid"])


if __name__ == "__main__":
    unittest.main()
