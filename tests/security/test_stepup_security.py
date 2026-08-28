"""
S02.4 — Agent Step-Up Security, Binding & Adversarial Defense Tests.
"""

import time
import unittest

from agent.stepup.errors import StepUpErrorCode, StepUpWorkflowError
from agent.stepup.manager import AgentStepUpManager
from agent.stepup.types import AgentStepUpDecision, HumanDecisionChoice


class TestStepUpSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = AgentStepUpManager()

    def test_ai_self_approval_blocked(self) -> None:
        """Verify AI agent identities cannot self-approve step-up challenges."""
        ch = self.manager.create_challenge(
            session_id="sess_sec_1",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH123",
            total_paise=550000,
        )

        ai_approvers = ["ag_shopper_01", "ai_agent", "bot:shopping_assistant", "agent:llm_model"]

        for ai_id in ai_approvers:
            decision = AgentStepUpDecision(
                challenge_id=ch.challenge_id,
                approver_id=ai_id,
                decision=HumanDecisionChoice.APPROVE,
            )
            with self.assertRaises(StepUpWorkflowError) as ctx:
                self.manager.resolve_decision(
                    decision=decision,
                    session_id="sess_sec_1",
                    buyer_id="b1",
                    merchant_id="m1",
                    current_cart_hash="HASH123",
                    current_total_paise=550000,
                    agent_id="ag_shopper_01",
                )
            self.assertEqual(ctx.exception.code, StepUpErrorCode.AI_SELF_APPROVAL_BLOCKED)

    def test_post_approval_price_tampering_rejected(self) -> None:
        """Verify modifying cart total price post-challenge creation raises STEP_UP_BINDING_MISMATCH."""
        ch = self.manager.create_challenge(
            session_id="sess_sec_2",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH123",
            total_paise=550000,  # Original price ₹5,500
        )

        decision = AgentStepUpDecision(
            challenge_id=ch.challenge_id,
            approver_id="user_human_buyer",
            decision=HumanDecisionChoice.APPROVE,
        )

        # Attacker tampered price to ₹7,500 paise
        with self.assertRaises(StepUpWorkflowError) as ctx:
            self.manager.resolve_decision(
                decision=decision,
                session_id="sess_sec_2",
                buyer_id="b1",
                merchant_id="m1",
                current_cart_hash="HASH123",
                current_total_paise=750000,  # Tampered price
                agent_id="ag_1",
            )
        self.assertEqual(ctx.exception.code, StepUpErrorCode.STEP_UP_BINDING_MISMATCH)

    def test_post_approval_cart_item_tampering_rejected(self) -> None:
        """Verify modifying cart items (cart hash mismatch) raises STEP_UP_BINDING_MISMATCH."""
        ch = self.manager.create_challenge(
            session_id="sess_sec_3",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH_ORIGINAL",
            total_paise=550000,
        )

        decision = AgentStepUpDecision(
            challenge_id=ch.challenge_id,
            approver_id="user_human_buyer",
            decision=HumanDecisionChoice.APPROVE,
        )

        # Attacker substituted item resulting in new cart hash
        with self.assertRaises(StepUpWorkflowError) as ctx:
            self.manager.resolve_decision(
                decision=decision,
                session_id="sess_sec_3",
                buyer_id="b1",
                merchant_id="m1",
                current_cart_hash="HASH_TAMPERED",
                current_total_paise=550000,
                agent_id="ag_1",
            )
        self.assertEqual(ctx.exception.code, StepUpErrorCode.STEP_UP_BINDING_MISMATCH)

    def test_expired_challenge_fails_closed(self) -> None:
        """Verify resolving an expired challenge fails closed with STEP_UP_CHALLENGE_EXPIRED."""
        ch = self.manager.create_challenge(
            session_id="sess_sec_4",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH123",
            total_paise=550000,
            ttl_seconds=0.01,  # 10 milliseconds TTL
        )

        time.sleep(0.02)  # Wait for TTL to expire

        decision = AgentStepUpDecision(
            challenge_id=ch.challenge_id,
            approver_id="user_human_buyer",
            decision=HumanDecisionChoice.APPROVE,
        )

        with self.assertRaises(StepUpWorkflowError) as ctx:
            self.manager.resolve_decision(
                decision=decision,
                session_id="sess_sec_4",
                buyer_id="b1",
                merchant_id="m1",
                current_cart_hash="HASH123",
                current_total_paise=550000,
                agent_id="ag_1",
            )
        self.assertEqual(ctx.exception.code, StepUpErrorCode.STEP_UP_CHALLENGE_EXPIRED)


if __name__ == "__main__":
    unittest.main()
