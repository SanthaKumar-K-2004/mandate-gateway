"""
S03.4 — Submission Readiness Unit Test Suite.

Tests SubmissionReadinessEngine, benchmark execution, and readiness DoD checklist.
"""

import unittest

from agent.submission.engine import SubmissionManager
from apps.api.domain.submission import EXPECTED_PROJECT_CONTEXT_SHA256, SubmissionReadinessEngine


class TestSubmissionReadinessUnit(unittest.TestCase):
    """Unit test cases for Submission Readiness Engine & Manager."""

    def setUp(self) -> None:
        self.engine = SubmissionReadinessEngine()
        self.manager = SubmissionManager()

    def test_evaluate_submission_readiness_dod(self) -> None:
        status = self.engine.evaluate_submission_readiness()
        self.assertTrue(status.is_submission_ready)
        self.assertEqual(status.satisfied_criteria_count, 22)
        self.assertEqual(status.total_criteria_count, 22)
        self.assertEqual(status.project_context_checksum, EXPECTED_PROJECT_CONTEXT_SHA256)
        self.assertTrue(status.criteria_status["ai_buyer_legitimate_purchase"])
        self.assertTrue(status.criteria_status["no_secrets_committed"])

    def test_run_performance_benchmarks(self) -> None:
        benchmarks = self.engine.run_performance_benchmarks()
        self.assertGreater(benchmarks.ed25519_signing_latency_ms, 0.0)
        self.assertGreater(benchmarks.rate_limiter_throughput_ops, 0.0)
        self.assertEqual(benchmarks.concurrency_workers_verified, 50)

    def test_manager_delegation(self) -> None:
        readiness = self.manager.get_readiness_status()
        self.assertTrue(readiness.is_submission_ready)

        benchmarks = self.manager.get_benchmarks()
        self.assertGreater(benchmarks.rate_limiter_throughput_ops, 0.0)

        matrix = self.manager.get_threat_matrix()
        self.assertTrue(matrix.all_attacks_fail_closed)


if __name__ == "__main__":
    unittest.main()
