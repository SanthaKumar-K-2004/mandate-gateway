"""
S02.7 — Red-Team API Endpoints Integration Tests.

Verifies end-to-end routing, payload handling, and contract serialization
for /api/redteam/* endpoints.
"""

import unittest

from agent.redteam.engine import RedTeamChaosEngine
from agent.redteam.types import AttackStatus, AttackType, RedTeamAttackRequest
from apps.api.contracts.redteam import RedTeamAttackResponse, RedTeamRunAllResponse
from apps.api.routers.redteam import (
    attack_cart_tamper,
    attack_double_spend,
    attack_expired_mandate,
    attack_merchant_policy,
    attack_prompt_injection,
    attack_replay,
    attack_timeout,
    attack_unauthorized_tool,
    run_all_attacks,
)


class TestRedTeamIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RedTeamChaosEngine()

    def test_endpoint_attack_1_prompt_injection(self) -> None:
        """Verify POST /api/redteam/prompt-injection handler returns valid response contract."""
        resp = attack_prompt_injection(
            request=RedTeamAttackRequest(attack_type=AttackType.PROMPT_INJECTION),
            engine=self.engine,
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_attack_2_cart_tamper(self) -> None:
        """Verify POST /api/redteam/cart-tamper handler returns valid response contract."""
        resp = attack_cart_tamper(
            request=RedTeamAttackRequest(attack_type=AttackType.CART_TAMPER), engine=self.engine
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_attack_3_replay(self) -> None:
        """Verify POST /api/redteam/replay handler returns valid response contract."""
        resp = attack_replay(
            request=RedTeamAttackRequest(attack_type=AttackType.NONCE_REPLAY), engine=self.engine
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_attack_4_double_spend(self) -> None:
        """Verify POST /api/redteam/double-spend handler returns valid response contract."""
        resp = attack_double_spend(
            request=RedTeamAttackRequest(attack_type=AttackType.DOUBLE_SPEND), engine=self.engine
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_attack_5_timeout(self) -> None:
        """Verify POST /api/redteam/timeout handler returns valid response contract."""
        resp = attack_timeout(
            request=RedTeamAttackRequest(attack_type=AttackType.TIMEOUT_RETRY), engine=self.engine
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_attack_6_expired_mandate(self) -> None:
        """Verify POST /api/redteam/expired-mandate handler returns valid response contract."""
        resp = attack_expired_mandate(
            request=RedTeamAttackRequest(attack_type=AttackType.EXPIRED_MANDATE), engine=self.engine
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_attack_7_merchant_policy(self) -> None:
        """Verify POST /api/redteam/merchant-policy handler returns valid response contract."""
        resp = attack_merchant_policy(
            request=RedTeamAttackRequest(attack_type=AttackType.MERCHANT_POLICY), engine=self.engine
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_attack_8_unauthorized_tool(self) -> None:
        """Verify POST /api/redteam/unauthorized-tool handler returns valid response contract."""
        resp = attack_unauthorized_tool(
            request=RedTeamAttackRequest(attack_type=AttackType.UNAUTHORIZED_TOOL),
            engine=self.engine,
        )
        self.assertIsInstance(resp, RedTeamAttackResponse)
        self.assertEqual(resp.status, AttackStatus.BLOCKED)

    def test_endpoint_run_all(self) -> None:
        """Verify POST /api/redteam/run-all handler executes full suite and returns summary."""
        resp = run_all_attacks(engine=self.engine)
        self.assertIsInstance(resp, RedTeamRunAllResponse)
        self.assertEqual(resp.total_attacks, 8)
        self.assertEqual(resp.total_blocked, 8)
        self.assertEqual(resp.total_exploited, 0)
        self.assertTrue(resp.all_passed)


if __name__ == "__main__":
    unittest.main()
