"""
S02.8 — Decision Trace & Explainability Engine Unit Tests.

Tests decision trace generation for ALLOW, STEP_UP_REQUIRED, and REJECT outcomes.
"""

import unittest

from agent.explainability.engine import ExplainabilityEngine
from agent.explainability.errors import ExplainabilityError
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.execution_engine import ExecutionResult
from apps.api.domain.types import (
    PaymentResultState,
    PolicyDecision,
    RejectionReason,
    TransactionState,
)


class TestExplainabilityEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ExplainabilityEngine()

    def test_allow_decision_trace_generation(self) -> None:
        """Verify generating decision trace for an ALLOW / AUTO_EXECUTE authorization."""
        auth_res = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=[
                SecurityControlOutcome(
                    control_name="MANDATE_EVALUATION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="MERCHANT_POLICY", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="CART_INTEGRITY", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="BUDGET_RESERVATION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="REPLAY_PROTECTION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="NONCE_VALIDATION", passed=True, decision=PolicyDecision.ALLOW
                ),
            ],
        )
        exec_res = ExecutionResult(
            success=True,
            transaction_id="tx_100",
            state=TransactionState.COMMITTED,
            external_reference="ord_razorpay_100",
            provider_status=PaymentResultState.SUCCESS,
        )

        report = self.engine.generate_trace(
            transaction_id="tx_100",
            authorization_result=auth_res,
            execution_result=exec_res,
            audit_event_id="evt_100",
            action_receipt_id="rec_100",
        )

        self.assertEqual(report.transaction_id, "tx_100")
        self.assertEqual(report.overall_decision, PolicyDecision.ALLOW)
        self.assertIn("All mandatory authorization constraints satisfied", report.summary_reason)
        self.assertIn("DECISION: AUTO_EXECUTE", report.formatted_text_trace)
        self.assertEqual(len(report.control_steps), 6)
        self.assertIn("ord_razorpay_100", report.razorpay_execution_status)

    def test_reject_decision_trace_generation(self) -> None:
        """Verify generating decision trace for a REJECT authorization."""
        auth_res = AuthorizationResult(
            decision=PolicyDecision.REJECT,
            control_outcomes=[
                SecurityControlOutcome(
                    control_name="MANDATE_EVALUATION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="CART_INTEGRITY",
                    passed=False,
                    decision=PolicyDecision.REJECT,
                    rejection_reason=RejectionReason.CART_INTEGRITY_VIOLATION,
                    detail="Digest mismatch",
                ),
            ],
        )

        report = self.engine.generate_trace(
            transaction_id="tx_101",
            authorization_result=auth_res,
        )

        self.assertEqual(report.overall_decision, PolicyDecision.REJECT)
        self.assertIn("CART_INTEGRITY", report.summary_reason)
        self.assertIn("DECISION: REJECT", report.formatted_text_trace)
        self.assertIn("NOT ATTEMPTED", report.razorpay_execution_status)

    def test_step_up_decision_trace_generation(self) -> None:
        """Verify generating decision trace for a STEP_UP_REQUIRED authorization."""
        auth_res = AuthorizationResult(
            decision=PolicyDecision.STEP_UP_REQUIRED,
            control_outcomes=[
                SecurityControlOutcome(
                    control_name="MANDATE_EVALUATION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="STEP_UP_AUTHORIZATION",
                    passed=False,
                    decision=PolicyDecision.STEP_UP_REQUIRED,
                    detail="Amount exceeds auto cap",
                ),
            ],
        )

        report = self.engine.generate_trace(
            transaction_id="tx_102",
            authorization_result=auth_res,
        )

        self.assertEqual(report.overall_decision, PolicyDecision.STEP_UP_REQUIRED)
        self.assertIn("DECISION: STEP_UP_REQUIRED", report.formatted_text_trace)
        self.assertIn("AWAITING CONFIRMATION", report.razorpay_execution_status)

    def test_empty_transaction_id_raises_explainability_error(self) -> None:
        """Verify empty transaction ID raises ExplainabilityError."""
        auth_res = AuthorizationResult(decision=PolicyDecision.ALLOW, control_outcomes=[])
        with self.assertRaises(ExplainabilityError):
            self.engine.generate_trace(transaction_id="", authorization_result=auth_res)


if __name__ == "__main__":
    unittest.main()
