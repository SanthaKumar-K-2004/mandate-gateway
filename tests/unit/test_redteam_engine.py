"""
S02.7 — Red-Team Chaos Engine Unit Tests.

Tests individual simulation of all 8 mandatory red-team attack vectors.
"""

import unittest

from agent.redteam.engine import RedTeamChaosEngine
from agent.redteam.types import AttackStatus, AttackType
from apps.api.domain.types import RejectionReason


class TestRedTeamEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RedTeamChaosEngine()

    def test_attack_1_prompt_injection(self) -> None:
        """Verify Attack 1 (Catalog Prompt Injection) is blocked."""
        res = self.engine.run_attack(AttackType.PROMPT_INJECTION)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(res.expected_rejection_reason, RejectionReason.TOOL_OUTSIDE_MANDATE.value)

    def test_attack_2_cart_tamper(self) -> None:
        """Verify Attack 2 (Cart Tampering) is blocked."""
        res = self.engine.run_attack(AttackType.CART_TAMPER)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(
            res.expected_rejection_reason, RejectionReason.CART_INTEGRITY_VIOLATION.value
        )

    def test_attack_3_nonce_replay(self) -> None:
        """Verify Attack 3 (Nonce Replay) is blocked."""
        res = self.engine.run_attack(AttackType.NONCE_REPLAY)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(
            res.expected_rejection_reason, RejectionReason.NONCE_ALREADY_CONSUMED.value
        )

    def test_attack_4_double_spend(self) -> None:
        """Verify Attack 4 (Concurrent Double Spend) is blocked."""
        res = self.engine.run_attack(AttackType.DOUBLE_SPEND)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(res.expected_rejection_reason, RejectionReason.BUDGET_EXCEEDED.value)

    def test_attack_5_timeout_retry(self) -> None:
        """Verify Attack 5 (Network Timeout Retry) is blocked/idempotent."""
        res = self.engine.run_attack(AttackType.TIMEOUT_RETRY)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(res.expected_rejection_reason, "DUPLICATE_EXECUTION_PREVENTED")

    def test_attack_6_expired_mandate(self) -> None:
        """Verify Attack 6 (Expired Mandate Execution) is blocked."""
        res = self.engine.run_attack(AttackType.EXPIRED_MANDATE)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(res.expected_rejection_reason, RejectionReason.MANDATE_EXPIRED.value)

    def test_attack_7_merchant_policy(self) -> None:
        """Verify Attack 7 (Merchant Policy Violation) is blocked."""
        res = self.engine.run_attack(AttackType.MERCHANT_POLICY)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(res.expected_rejection_reason, RejectionReason.AI_COMMERCE_DISABLED.value)

    def test_attack_8_unauthorized_tool(self) -> None:
        """Verify Attack 8 (Direct Call to Masked MCP Tool) is blocked."""
        res = self.engine.run_attack(AttackType.UNAUTHORIZED_TOOL)
        self.assertEqual(res.status, AttackStatus.BLOCKED)
        self.assertEqual(res.expected_rejection_reason, RejectionReason.METHOD_NOT_AUTHORIZED.value)

    def test_run_all_attacks(self) -> None:
        """Verify running full red-team suite executes all 8 attacks with 100% BLOCKED status."""
        results = self.engine.run_all_attacks()
        self.assertEqual(len(results), 8)
        self.assertTrue(all(r.status == AttackStatus.BLOCKED for r in results))


if __name__ == "__main__":
    unittest.main()
