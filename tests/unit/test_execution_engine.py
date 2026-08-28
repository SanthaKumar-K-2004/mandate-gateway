"""
Unit test suite for S01.11 Payment Execution Engine & Boundary.
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


class TestPaymentExecutionEngineUnit(unittest.TestCase):
    """Exhaustive unit test suite for S01.11 PaymentExecutionService."""

    def setUp(self) -> None:
        self.adapter = MockRazorpayAdapter()
        self.service = PaymentExecutionService(self.adapter)

        self.transaction_id = "tx-exec-100"
        self.buyer_id = "buyer-100"
        self.merchant_id = "merchant-100"
        self.mandate_id = "mandate-100"
        self.cart_hash = "a" * 64
        self.amount_paise = 50000
        self.currency = Currency.INR

        self.transaction = Transaction(
            transaction_id=self.transaction_id,
            buyer_id=self.buyer_id,
            merchant_id=self.merchant_id,
            mandate_id=self.mandate_id,
            mandate_version=1,
            policy_version=1,
            cart_hash=self.cart_hash,
            amount_paise=self.amount_paise,
            currency=self.currency,
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

        self.valid_auth_result = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=self.valid_outcomes,
            decision_trace={"authorization_reference": "auth_ref_100"},
        )

        self.valid_proposal = PaymentExecuteProposalRequest(
            transaction_id=self.transaction_id,
            merchant_id=self.merchant_id,
            buyer_id=self.buyer_id,
            mandate_id=self.mandate_id,
            amount_paise=self.amount_paise,
            currency=self.currency,
            cart_hash=self.cart_hash,
            operation=McpOperation.CREATE_ORDER,
            idempotency_key=f"exec:{self.transaction_id}",
        )

    # ------------------------------------------------------------------
    # 1. Happy-Path Execution
    # ------------------------------------------------------------------

    def test_happy_path_payment_execution_succeeds(self) -> None:
        res = self.service.execute_payment(
            proposal=self.valid_proposal,
            authorization_result=self.valid_auth_result,
            transaction=self.transaction,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.state, TransactionState.COMMITTED)
        self.assertIsNotNone(res.external_reference)
        self.assertEqual(res.provider_status, PaymentResultState.SUCCESS)

    # ------------------------------------------------------------------
    # 2. Authorization Precondition Failures (Fail-Closed)
    # ------------------------------------------------------------------

    def test_execution_rejected_when_authorization_decision_is_reject(self) -> None:
        reject_auth = AuthorizationResult(
            decision=PolicyDecision.REJECT,
            control_outcomes=self.valid_outcomes,
            rejection_reason=RejectionReason.MANDATE_EXPIRED,
        )
        res = self.service.execute_payment(
            proposal=self.valid_proposal,
            authorization_result=reject_auth,
            transaction=self.transaction,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.state, TransactionState.REJECTED)
        self.assertEqual(res.failure_category, ExecutionFailureCategory.AUTHORIZATION_FAILED)

    def test_execution_rejected_when_missing_required_security_control(self) -> None:
        incomplete_outcomes = self.valid_outcomes[:-1]  # drop NONCE_VALIDATION
        incomplete_auth = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=incomplete_outcomes,
        )
        res = self.service.execute_payment(
            proposal=self.valid_proposal,
            authorization_result=incomplete_auth,
            transaction=self.transaction,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.failure_code, RejectionReason.CONTROL_RESULT_MISSING)

    # ------------------------------------------------------------------
    # 3. Context Mismatch Integrity Checks
    # ------------------------------------------------------------------

    def test_execution_rejected_on_amount_mismatch(self) -> None:
        tampered_proposal = self.valid_proposal.model_copy(update={"amount_paise": 50001})
        res = self.service.execute_payment(
            proposal=tampered_proposal,
            authorization_result=self.valid_auth_result,
            transaction=self.transaction,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.failure_code, RejectionReason.INVALID_AMOUNT)
        self.assertEqual(res.failure_category, ExecutionFailureCategory.INVALID_CONTEXT)

    def test_execution_rejected_on_currency_mismatch(self) -> None:
        tampered_proposal = self.valid_proposal.model_copy(update={"currency": Currency.USD})
        res = self.service.execute_payment(
            proposal=tampered_proposal,
            authorization_result=self.valid_auth_result,
            transaction=self.transaction,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.failure_code, RejectionReason.CURRENCY_MISMATCH)

    def test_execution_rejected_on_merchant_mismatch(self) -> None:
        tampered_proposal = self.valid_proposal.model_copy(
            update={"merchant_id": "merchant-hacked"}
        )
        res = self.service.execute_payment(
            proposal=tampered_proposal,
            authorization_result=self.valid_auth_result,
            transaction=self.transaction,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.failure_code, RejectionReason.MERCHANT_MISMATCH)

    def test_execution_rejected_on_cart_hash_mismatch(self) -> None:
        tampered_proposal = self.valid_proposal.model_copy(update={"cart_hash": "f" * 64})
        res = self.service.execute_payment(
            proposal=tampered_proposal,
            authorization_result=self.valid_auth_result,
            transaction=self.transaction,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.failure_code, RejectionReason.CART_INTEGRITY_VIOLATION)

    # ------------------------------------------------------------------
    # 4. Operation Allowlisting
    # ------------------------------------------------------------------

    def test_execution_rejected_for_blocked_payout_operation(self) -> None:
        payout_proposal = self.valid_proposal.model_copy(update={"operation": McpOperation.PAYOUT})
        res = self.service.execute_payment(
            proposal=payout_proposal,
            authorization_result=self.valid_auth_result,
            transaction=self.transaction,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.failure_code, RejectionReason.OPERATION_NOT_ALLOWED)

    # ------------------------------------------------------------------
    # 5. Transaction State Graph Safety
    # ------------------------------------------------------------------

    def test_execution_rejected_if_transaction_in_draft_state(self) -> None:
        draft_tx = self.transaction.model_copy(update={"state": TransactionState.DRAFT})
        res = self.service.execute_payment(
            proposal=self.valid_proposal,
            authorization_result=self.valid_auth_result,
            transaction=draft_tx,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.failure_code, RejectionReason.INVALID_TRANSACTION_STATE)


if __name__ == "__main__":
    unittest.main()
