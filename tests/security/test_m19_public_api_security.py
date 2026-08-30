"""
M19 Public API Security Adversarial Test Suite
=============================================
Workstream 10 — Evaluates public API security boundaries, header injection,
cross-tenant IDOR isolation, and request ID tampering protection.
"""

from __future__ import annotations

import unittest
from apps.api.app.factory import create_fastapi_app


class TestM19PublicAPISecurity(unittest.TestCase):
    """Adversarial security test suite for public API endpoints."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        if not self.app:
            self.skipTest("FastAPI not installed")
        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    def test_01_payload_too_large_rejection(self) -> None:
        """Verify API rejects requests exceeding MAX_REQUEST_SIZE_BYTES (1MB)."""
        huge_body = "A" * (1_048_576 + 100)
        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(huge_body)),
        }
        res = self.client.post("/api/webhooks/subscriptions", content=huge_body, headers=headers)
        self.assertEqual(res.status_code, 413)
        data = res.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "PAYLOAD_TOO_LARGE")

    def test_02_request_id_sanitization(self) -> None:
        """Verify malicious or oversized X-Request-ID headers are sanitized safely."""
        huge_req_id = "req_" + ("X" * 300)
        headers = {"X-Request-ID": huge_req_id}
        res = self.client.get("/health/live", headers=headers)
        self.assertEqual(res.status_code, 200)
        # Should sanitize and replace with a generated safe req_ id of normal length
        resp_req_id = res.headers.get("X-Request-ID", "")
        self.assertTrue(len(resp_req_id) <= 128)

    def test_03_cross_tenant_access_rejection(self) -> None:
        """Verify multi-tenant isolation rejects unauthorized cross-merchant access."""
        from apps.api.domain.identity import AuthenticatedPrincipal, validate_merchant_access

        principal = AuthenticatedPrincipal(
            credential_id="cred_m1",
            merchant_id="mer_tenant_A",
            scopes={"transaction:write"},
        )
        # Same tenant -> Pass
        validate_merchant_access(principal, "mer_tenant_A")

        # Cross tenant -> Raise PermissionError
        with self.assertRaises(PermissionError):
            validate_merchant_access(principal, "mer_tenant_B")


if __name__ == "__main__":
    unittest.main()
