"""
Integration test suite for S01.11 Payment Execution Boundary with MockRazorpayAdapter.
"""

import unittest

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.execution import ExecutionFailureCategory
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    Currency,
    McpOperation,
    PaymentResultState,
    PolicyDecision,
    RejectionReason,
    TransactionState,
)


class TestPaymentExecutionIntegration(unittest.TestCase):
    """Integration test suite for S01.11 provider failure matrix & state machine."""

    def setUp(self) -> None:
        self.adapter = MockRazorpayAdapter()
        self.service = PaymentExecutionService(self.adapter)

        self.transaction_id = "tx-integ-100"
        self.transaction = Transaction(
            transaction_id=self.transaction_id,
            buyer_id="buyer-integ",
            merchant_id="merchant-integ",
            mandate_id="mandate-integ",
            mandate_version=1,
            policy_version=1,
            cart_hash="d" * 64,
            amount_paise=30000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
        )

        self.valid_outcomes = [
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
        ]
        self.auth_allow = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=self.valid_outcomes,
        )

        self.proposal = PaymentExecuteProposalRequest(
            transaction_id=self.transaction_id,
            merchant_id="merchant-integ",
            buyer_id="buyer-integ",
            mandate_id="mandate-integ",
            amount_paise=30000,
            currency=Currency.INR,
            cart_hash="d" * 64,
            operation=McpOperation.CREATE_ORDER,
            idempotency_key=f"exec:{self.transaction_id}",
        )

    # ------------------------------------------------------------------
    # 1. Provider Rejection Flow
    # ------------------------------------------------------------------

    def test_provider_rejection_transitions_to_rolled_back(self) -> None:
        self.adapter.set_next_failure(
            category=ExecutionFailureCategory.PROVIDER_REJECTED,
            reason=RejectionReason.METHOD_NOT_AUTHORIZED,
            message="Card issuer rejected payment",
        )
        res = self.service.execute_payment(
            proposal=self.proposal,
            authorization_result=self.auth_allow,
            transaction=self.transaction,
        )

        self.assertFalse(res.success)
        self.assertEqual(res.state, TransactionState.ROLLED_BACK)
        self.assertEqual(res.failure_category, ExecutionFailureCategory.PROVIDER_REJECTED)
        self.assertEqual(res.provider_status, PaymentResultState.FAILED)

    # ------------------------------------------------------------------
    # 2. Timeout & Unknown Provider Outcome Flow
    # ------------------------------------------------------------------

    def test_provider_timeout_preserves_unknown_outcome_safety(self) -> None:
        self.adapter.set_simulate_timeout(True)
        res = self.service.execute_payment(
            proposal=self.proposal,
            authorization_result=self.auth_allow,
            transaction=self.transaction,
        )

        self.assertFalse(res.success)
        self.assertEqual(res.state, TransactionState.ROLLED_BACK)
        self.assertEqual(res.failure_category, ExecutionFailureCategory.TIMEOUT)
        self.assertEqual(res.provider_status, PaymentResultState.UNKNOWN)

    # ------------------------------------------------------------------
    # 3. Connection Error Flow
    # ------------------------------------------------------------------

    def test_provider_connection_error_handled_safely(self) -> None:
        self.adapter.set_simulate_connection_error(True)
        res = self.service.execute_payment(
            proposal=self.proposal,
            authorization_result=self.auth_allow,
            transaction=self.transaction,
        )

        self.assertFalse(res.success)
        self.assertEqual(res.failure_category, ExecutionFailureCategory.CONNECTION_FAILED)


if __name__ == "__main__":
    unittest.main()
