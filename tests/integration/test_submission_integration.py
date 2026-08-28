"""
S03.4 — Submission Readiness Integration Test Suite.

Tests FastAPI endpoints `/api/submission/readiness`, `/api/submission/benchmarks`,
and `/api/submission/threat-matrix` (Section 36 & Section 41, PROJECT_CONTEXT.md).
"""

import unittest
from fastapi.testclient import TestClient

from apps.api.app.factory import create_fastapi_app
from apps.api.domain.submission import EXPECTED_PROJECT_CONTEXT_SHA256


class TestSubmissionIntegration(unittest.TestCase):
    """Integration test cases for S03.4 Submission REST API router."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        self.assertIsNotNone(self.app)
        self.client = TestClient(self.app)

    def test_get_submission_readiness_endpoint(self) -> None:
        resp = self.client.get("/api/submission/readiness")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_submission_ready"])
        self.assertEqual(data["satisfied_criteria_count"], 22)
        self.assertEqual(data["project_context_checksum"], EXPECTED_PROJECT_CONTEXT_SHA256)

    def test_get_benchmarks_endpoint(self) -> None:
        resp = self.client.get("/api/submission/benchmarks")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["ed25519_signing_latency_ms"], 0.0)
        self.assertGreater(data["rate_limiter_throughput_ops"], 0.0)
        self.assertEqual(data["concurrency_workers_verified"], 50)

    def test_get_threat_matrix_endpoint(self) -> None:
        resp = self.client.get("/api/submission/threat-matrix")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["all_attacks_fail_closed"])
        self.assertTrue(data["prompt_injection_blocked"])


if __name__ == "__main__":
    unittest.main()
