"""
M04 — System Hardening Security & Adversarial Test Suite.
"""

import unittest

from apps.api.domain.system_hardening import EXPECTED_PROJECT_CONTEXT_SHA256, SystemHardeningEngine


class TestM04HardeningSecurity(unittest.TestCase):
    """Security test suite for M04 system hardening and fail-closed posture."""

    def setUp(self) -> None:
        self.engine = SystemHardeningEngine()

    def test_project_context_hash_invariant(self) -> None:
        self.assertEqual(
            EXPECTED_PROJECT_CONTEXT_SHA256,
            "2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a",
        )

    def test_36_adversarial_scenarios_verified(self) -> None:
        res = self.engine.verify_36_adversarial_scenarios()
        self.assertTrue(all(res.values()))
        self.assertTrue(res["prompt_injection_blocked"])
        self.assertTrue(res["authority_injection_blocked"])
        self.assertTrue(res["cart_tampering_blocked"])
