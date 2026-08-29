"""
M14 Production Security Acceptance & End-to-End Certification Tests
"""

import unittest
from apps.api.app.factory import create_fastapi_app
from fastapi.testclient import TestClient


class TestM14ProductionSecurityAcceptance(unittest.TestCase):
    """Production acceptance certification for all M14 security controls."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        self.client = TestClient(self.app)

    def test_full_security_acceptance_pipeline(self) -> None:
        # 1. Unauthenticated internal endpoint check -> 401
        r1 = self.client.get("/internal/operations/alerts")
        self.assertEqual(r1.status_code, 401)

        # 2. Oversized payload -> 413
        large_body = "a" * (1024 * 1024 + 10)
        r2 = self.client.post(
            "/api/v1/merchants",
            content=large_body,
            headers={"Content-Length": str(len(large_body))},
        )
        self.assertEqual(r2.status_code, 413)

        # 3. Public liveness probe -> 200
        r3 = self.client.get("/health/live")
        self.assertEqual(r3.status_code, 200)

        # 4. Valid operator access -> 200
        r4 = self.client.get(
            "/internal/operations/alerts",
            headers={"X-Operator-Token": "rzp_live_operator_token_123"},
        )
        self.assertEqual(r4.status_code, 200)


if __name__ == "__main__":
    unittest.main()
