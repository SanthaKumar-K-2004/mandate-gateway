import unittest

from agent.stepup.errors import StepUpErrorCode, StepUpWorkflowError
from agent.stepup.manager import AgentStepUpManager
from agent.stepup.types import AgentStepUpDecision, HumanDecisionChoice, StepUpStatus


class TestStepUpManagerUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = AgentStepUpManager()

    def test_create_and_get_challenge(self) -> None:
        ch = self.manager.create_challenge(
            session_id="sess_1",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH123",
            total_paise=550000,
        )
        self.assertEqual(ch.status, StepUpStatus.PENDING)
        self.assertEqual(ch.session_id, "sess_1")

        active = self.manager.get_active_challenge_for_session("sess_1")
        self.assertIsNotNone(active)
        assert active is not None
        self.assertEqual(active.challenge_id, ch.challenge_id)

    def test_resolve_approve_decision(self) -> None:
        ch = self.manager.create_challenge(
            session_id="sess_2",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH123",
            total_paise=550000,
        )

        decision = AgentStepUpDecision(
            challenge_id=ch.challenge_id,
            approver_id="user_buyer_001",
            decision=HumanDecisionChoice.APPROVE,
        )

        resolved = self.manager.resolve_decision(
            decision=decision,
            session_id="sess_2",
            buyer_id="b1",
            merchant_id="m1",
            current_cart_hash="HASH123",
            current_total_paise=550000,
            agent_id="agent_1",
        )

        self.assertEqual(resolved.status, StepUpStatus.APPROVED)

    def test_resolve_reject_decision(self) -> None:
        ch = self.manager.create_challenge(
            session_id="sess_3",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH123",
            total_paise=550000,
        )

        decision = AgentStepUpDecision(
            challenge_id=ch.challenge_id,
            approver_id="user_buyer_001",
            decision=HumanDecisionChoice.REJECT,
        )

        resolved = self.manager.resolve_decision(
            decision=decision,
            session_id="sess_3",
            buyer_id="b1",
            merchant_id="m1",
            current_cart_hash="HASH123",
            current_total_paise=550000,
            agent_id="agent_1",
        )

        self.assertEqual(resolved.status, StepUpStatus.REJECTED)

    def test_challenge_not_found_raises(self) -> None:
        decision = AgentStepUpDecision(
            challenge_id="non_existent_stepup",
            approver_id="user_buyer_001",
            decision=HumanDecisionChoice.APPROVE,
        )
        with self.assertRaises(StepUpWorkflowError) as ctx:
            self.manager.resolve_decision(
                decision=decision,
                session_id="sess_4",
                buyer_id="b1",
                merchant_id="m1",
                current_cart_hash="HASH123",
                current_total_paise=550000,
            )
        self.assertEqual(ctx.exception.code, StepUpErrorCode.STEP_UP_NOT_FOUND)

    def test_already_resolved_challenge_raises(self) -> None:
        ch = self.manager.create_challenge(
            session_id="sess_5",
            buyer_id="b1",
            merchant_id="m1",
            mandate_id="man1",
            cart_hash="HASH123",
            total_paise=550000,
        )
        decision = AgentStepUpDecision(
            challenge_id=ch.challenge_id,
            approver_id="user_buyer_001",
            decision=HumanDecisionChoice.APPROVE,
        )
        self.manager.resolve_decision(
            decision=decision,
            session_id="sess_5",
            buyer_id="b1",
            merchant_id="m1",
            current_cart_hash="HASH123",
            current_total_paise=550000,
        )

        # Re-resolving must raise STEP_UP_ALREADY_RESOLVED
        with self.assertRaises(StepUpWorkflowError) as ctx:
            self.manager.resolve_decision(
                decision=decision,
                session_id="sess_5",
                buyer_id="b1",
                merchant_id="m1",
                current_cart_hash="HASH123",
                current_total_paise=550000,
            )
        self.assertEqual(ctx.exception.code, StepUpErrorCode.STEP_UP_ALREADY_RESOLVED)


if __name__ == "__main__":
    unittest.main()
