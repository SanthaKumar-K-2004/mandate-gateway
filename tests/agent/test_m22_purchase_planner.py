"""
M22 Purchase Planning Engine & Confirmation Gate Unit Test Suite
==================================================================
Workstreams 6 & 7 — Verifies purchase planning flow, product candidate selection,
confirmation token generation, token tampering rejection, and token single-use replay protection.
"""

from __future__ import annotations

import unittest
from apps.api.agent.confirmation_gate import ConfirmationError, HumanConfirmationGate
from apps.api.agent.models import AgentRequest
from apps.api.agent.purchase_planner import PurchasePlanner


class TestM22PurchasePlanner(unittest.TestCase):
    """Purchase planner and confirmation gate test suite."""

    def setUp(self) -> None:
        self.gate = HumanConfirmationGate(secret_key="test_secret_key_123")
        self.planner = PurchasePlanner(confirmation_gate=self.gate)

    def test_01_process_request_generates_plan_and_token(self) -> None:
        """Verify processing 'Buy me a coffee under ₹200' generates plan and valid confirmation token."""
        req = AgentRequest(
            request_id="req_agent_001",
            merchant_id="mer_cafe_acme",
            buyer_id="buy_user_101",
            prompt="Buy me a coffee under ₹200",
        )
        decision = self.planner.process_request(req)
        self.assertEqual(decision.status, "AWAITING_CONFIRMATION")
        self.assertIsNotNone(decision.purchase_plan)
        plan = decision.purchase_plan
        assert plan is not None
        self.assertTrue(
            any(w in plan.product_name.lower() for w in ["coffee", "café", "bean", "item"])
        )
        self.assertGreater(plan.amount_paise, 0)
        self.assertLessEqual(plan.amount_paise, 20000)
        assert plan.confirmation_token is not None
        self.assertTrue(plan.confirmation_token.startswith("cnf_"))

    def test_02_confirmation_token_verification_and_replay_rejection(self) -> None:
        """Verify token verification succeeds once and rejects replay on second attempt."""
        token_data = self.gate.generate_token(
            request_id="req_001",
            merchant_id="mer_01",
            buyer_id="buy_01",
            amount_paise=18000,
            currency="INR",
            ttl_seconds=600,
        )
        token = token_data["confirmation_token"]
        expires_at = token_data["expires_at"]

        # First verification must succeed
        valid = self.gate.verify_and_consume_token(
            confirmation_token=token,
            request_id="req_001",
            merchant_id="mer_01",
            buyer_id="buy_01",
            amount_paise=18000,
            currency="INR",
            expires_at=expires_at,
        )
        self.assertTrue(valid)

        # Second verification (replay attempt) must raise ConfirmationError
        with self.assertRaises(ConfirmationError):
            self.gate.verify_and_consume_token(
                confirmation_token=token,
                request_id="req_001",
                merchant_id="mer_01",
                buyer_id="buy_01",
                amount_paise=18000,
                currency="INR",
                expires_at=expires_at,
            )

    def test_03_tampered_amount_rejection(self) -> None:
        """Verify altering amount in token payload causes verification failure."""
        token_data = self.gate.generate_token(
            request_id="req_001",
            merchant_id="mer_01",
            buyer_id="buy_01",
            amount_paise=18000,
            ttl_seconds=600,
        )
        token = token_data["confirmation_token"]
        expires_at = token_data["expires_at"]

        # Attempt to confirm with altered amount 50000 Paise
        with self.assertRaises(ConfirmationError):
            self.gate.verify_and_consume_token(
                confirmation_token=token,
                request_id="req_001",
                merchant_id="mer_01",
                buyer_id="buy_01",
                amount_paise=50000,
                expires_at=expires_at,
            )


if __name__ == "__main__":
    unittest.main()
