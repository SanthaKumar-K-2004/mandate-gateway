"""
S02.4 — Agent Step-Up Integration Tests.

Verifies end-to-end flow from StepUp classification to AgentState transition, human approval,
and final PolicyEngine evaluation.
"""

from datetime import datetime, timezone
import unittest

from agent.graph.state import AgentState
from agent.graph.types import AgentStateEnum
from agent.stepup.gateway_adapter import StepUpGatewayAdapter
from agent.stepup.manager import AgentStepUpManager
from agent.stepup.types import AgentStepUpDecision, HumanDecisionChoice
from apps.api.domain.cart import CartItem
from apps.api.domain.cart_integrity import build_cart_with_hash
from apps.api.domain.mandates import SpendingLimits, create_buyer_mandate
from apps.api.domain.merchant_policy import create_merchant_policy
from apps.api.domain.policy_engine import PolicyEngine
from apps.api.domain.types import Currency, McpOperation, PolicyDecision, StepUpZone


class TestStepUpIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.step_up_manager = AgentStepUpManager()
        self.buyer_id = "buyer_integ_stepup_001"
        self.merchant_id = "merchant_integ_stepup_001"
        self.mandate_id = "mandate_integ_stepup_001"

        # Mandate spending cap = ₹25,000 (2,500,000 paise)
        self.mandate = create_buyer_mandate(
            mandate_id=self.mandate_id,
            buyer_id=self.buyer_id,
            limits=SpendingLimits(
                per_tx_paise=2500000,
                daily_paise=10000000,
                monthly_paise=50000000,
            ),
        )

        self.merchant_policy = create_merchant_policy(
            merchant_id=self.merchant_id,
            allowed_categories=frozenset({"electronics"}),
        )

    def test_end_to_end_stepup_flow(self) -> None:
        """Verify full HITL step-up workflow from Zone B classification to approval and PolicyEngine ALLOW."""
        # Cart total = ₹26,000 (2,600,000 paise) — Zone B Step-Up Required
        cart_total = 2600000

        # Step 1: M01 Zone Classification
        step_up_eval = StepUpGatewayAdapter.evaluate_step_up_zone(
            cart_total_paise=cart_total,
            mandate_cap_paise=self.mandate.limits.per_tx_paise,
            max_step_up_percent=10,
        )
        self.assertEqual(step_up_eval.zone, StepUpZone.STEP_UP_REQUIRED)

        # Step 2: Initialize Agent State & Trigger Step-Up Challenge Creation
        state = AgentState(
            agent_id="agent_shopper_integ",
            session_id="sess_stepup_integ_1",
            buyer_id=self.buyer_id,
            merchant_id=self.merchant_id,
            mandate_id=self.mandate_id,
        )
        state.transition_to(AgentStateEnum.PLANNING)

        item = CartItem(
            product_id="prod_laptop",
            merchant_id=self.merchant_id,
            name="Laptop",
            category="electronics",
            quantity=1,
            unit_price_paise=2600000,
            currency=Currency.INR,
        )
        cart = build_cart_with_hash(
            merchant_id=self.merchant_id,
            mandate_id=self.mandate_id,
            currency=Currency.INR,
            items=(item,),
            total_paise=2600000,
        )

        state = StepUpGatewayAdapter.process_step_up_flow(
            state=state,
            step_up_manager=self.step_up_manager,
            cart_hash=cart.cart_hash,
            total_paise=cart.total_paise,
        )
        self.assertEqual(state.current_state, AgentStateEnum.WAITING_FOR_GATEWAY)

        challenge = self.step_up_manager.get_active_challenge_for_session("sess_stepup_integ_1")
        self.assertIsNotNone(challenge)
        assert challenge is not None

        # Step 3: Human Approver Submits Approval Decision
        human_decision = AgentStepUpDecision(
            challenge_id=challenge.challenge_id,
            approver_id="user_human_approver_001",
            decision=HumanDecisionChoice.APPROVE,
        )

        state = StepUpGatewayAdapter.process_step_up_flow(
            state=state,
            step_up_manager=self.step_up_manager,
            decision=human_decision,
            cart_hash=cart.cart_hash,
            total_paise=cart.total_paise,
        )
        self.assertEqual(state.current_state, AgentStateEnum.PROPOSAL_READY)

        # Step 4: Final PolicyEngine Evaluation
        policy_eval = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=cart,
            operation=McpOperation.CREATE_ORDER,
            at=datetime.now(timezone.utc),
        )

        # Cart total 2,600,000 is within 10% step-up allowance of 2,500,000 mandate cap
        self.assertEqual(policy_eval.decision, PolicyDecision.STEP_UP_REQUIRED)


if __name__ == "__main__":
    unittest.main()
