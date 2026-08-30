"""
M22 AI Agent Demo Scenarios Test Suite
======================================
Workstream 13 — Verifies 4 deterministic demo scenarios:
  Scenario 1: "Buy coffee under ₹200"
  Scenario 2: "Find a product under ₹500 but do not purchase"
  Scenario 3: "Try to exceed my budget"
  Scenario 4: "Attempt confirmation replay"
"""

from __future__ import annotations

import unittest
from apps.api.agent.confirmation_gate import ConfirmationError, HumanConfirmationGate
from apps.api.agent.models import AgentRequest
from apps.api.agent.purchase_planner import PurchasePlanner


class TestM22DemoScenarios(unittest.TestCase):
    """AI agent demo scenarios test suite."""

    def setUp(self) -> None:
        self.gate = HumanConfirmationGate(secret_key="demo_secret_key_981")
        self.planner = PurchasePlanner(confirmation_gate=self.gate)

    def test_scenario_1_buy_coffee_under_200(self) -> None:
        """Scenario 1: User says 'Buy coffee under ₹200'. Formulates valid plan and confirmation token."""
        req = AgentRequest(
            request_id="req_demo_scen_1",
            merchant_id="mer_cafe_acme",
            buyer_id="buy_user_101",
            prompt="Buy coffee under ₹200",
        )
        decision = self.planner.process_request(req)
        self.assertEqual(decision.status, "AWAITING_CONFIRMATION")
        self.assertIsNotNone(decision.purchase_plan)
        plan = decision.purchase_plan
        assert plan is not None
        self.assertGreater(plan.amount_paise, 0)
        self.assertLessEqual(plan.amount_paise, 20000)
        self.assertIn("Coffee", plan.product_name)
        assert plan.confirmation_token is not None
        self.assertTrue(plan.confirmation_token.startswith("cnf_"))

    def test_scenario_2_search_without_purchase(self) -> None:
        """Scenario 2: User says 'Find a product under ₹500 but do not purchase'. Does not require confirmation."""
        req = AgentRequest(
            request_id="req_demo_scen_2",
            merchant_id="mer_cafe_acme",
            buyer_id="buy_user_101",
            prompt="Find a product under ₹500 but do not purchase",
        )
        decision = self.planner.process_request(req)
        self.assertEqual(decision.status, "PLANNING")
        assert decision.purchase_plan is not None
        self.assertFalse(decision.purchase_plan.requires_confirmation)

    def test_scenario_3_budget_exceed(self) -> None:
        """Scenario 3: User attempts budget exceed. Plan created with high amount requiring confirmation."""
        req = AgentRequest(
            request_id="req_demo_scen_3",
            merchant_id="mer_cafe_acme",
            buyer_id="buy_user_101",
            prompt="Try to exceed my budget",
        )
        decision = self.planner.process_request(req)
        self.assertEqual(decision.status, "AWAITING_CONFIRMATION")
        assert decision.purchase_plan is not None
        self.assertGreater(decision.purchase_plan.amount_paise, 0)

    def test_scenario_4_confirmation_replay_rejection(self) -> None:
        """Scenario 4: Attempting to reuse confirmation token is rejected by confirmation gate."""
        token_data = self.gate.generate_token(
            request_id="req_demo_scen_4",
            merchant_id="mer_cafe_acme",
            buyer_id="buy_user_101",
            amount_paise=18000,
        )
        token = token_data["confirmation_token"]

        # First verification succeeds
        self.assertTrue(
            self.gate.verify_and_consume_token(
                confirmation_token=token,
                request_id="req_demo_scen_4",
                merchant_id="mer_cafe_acme",
                buyer_id="buy_user_101",
                amount_paise=18000,
            )
        )

        # Second verification (replay) fails closed
        with self.assertRaises(ConfirmationError):
            self.gate.verify_and_consume_token(
                confirmation_token=token,
                request_id="req_demo_scen_4",
                merchant_id="mer_cafe_acme",
                buyer_id="buy_user_101",
                amount_paise=18000,
            )


if __name__ == "__main__":
    unittest.main()
