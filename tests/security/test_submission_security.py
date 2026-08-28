"""
S03.4 — Submission Security Test Suite.

Tests threat matrix reporting, project context SHA256 integrity, and fail-closed posture.
"""

import unittest

from agent.submission.engine import SubmissionManager
from apps.api.domain.submission import EXPECTED_PROJECT_CONTEXT_SHA256, SubmissionReadinessEngine


class TestSubmissionSecurity(unittest.TestCase):
    """Security test cases for S03.4 Submission Readiness."""

    def setUp(self) -> None:
        self.engine = SubmissionReadinessEngine()
        self.manager = SubmissionManager()

    def test_threat_matrix_all_attacks_fail_closed(self) -> None:
        matrix = self.engine.get_threat_matrix_evidence()
        self.assertTrue(matrix.prompt_injection_blocked)
        self.assertTrue(matrix.tool_masking_blocked)
        self.assertTrue(matrix.cart_tampering_blocked)
        self.assertTrue(matrix.budget_race_blocked)
        self.assertTrue(matrix.replay_nonce_blocked)
        self.assertTrue(matrix.expired_mandate_blocked)
        self.assertTrue(matrix.step_up_escalated)
        self.assertTrue(matrix.audit_chain_verified)
        self.assertTrue(matrix.all_attacks_fail_closed)

    def test_project_context_checksum_match(self) -> None:
        status = self.engine.evaluate_submission_readiness()
        self.assertEqual(status.project_context_checksum, EXPECTED_PROJECT_CONTEXT_SHA256)


if __name__ == "__main__":
    unittest.main()
