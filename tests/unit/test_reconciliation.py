"""
Unit test suite for S01.11.1 — Unknown Payment Outcome & Status Reconciliation Matrix.

Tests all cases (Case A through Case F):
- Case A: Request never reached provider -> FAILED -> ROLLED_BACK.
- Case B: Provider succeeded, response timed out -> initial UNKNOWN (EXECUTING), reconciled to SUCCESS (COMMITTED).
- Case C: Provider failed, response timed out -> initial UNKNOWN (EXECUTING), reconciled to FAILED (ROLLED_BACK).
- Case D: Provider status lookup times out -> remains UNKNOWN (EXECUTING).
- Case E: Provider status lookup returns malformed response -> remains UNKNOWN (EXECUTING).
- Case F: Payment already captured -> reconciled to COMMITTED without second execution dispatch.
"""

import unittest
from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult, SecurityControlOutcome
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.execution import ExecutionFailureCategory
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    Currency,
    McpOperation,
    PaymentResultState,
    PolicyDecision,
    RejectionReason,
    TransactionState,
)


def _make_allowed_auth_result() -> AuthorizationResult:
    return AuthorizationResult(
        decision=PolicyDecision.ALLOW,
        control_outcomes=[
            SecurityControlOutcome(
                control_name="MANDATE_EVALUATION",
                passed=True,
                decision=PolicyDecision.ALLOW,
            ),
            SecurityControlOutcome(
                control_name="MERCHANT_POLICY",
                passed=True,
                decision=PolicyDecision.ALLOW,
            ),
            SecurityControlOutcome(
                control_name="CART_INTEGRITY",
                passed=True,
                decision=PolicyDecision.ALLOW,
            ),
            SecurityControlOutcome(
                control_name="BUDGET_RESERVATION",
                passed=True,
                decision=PolicyDecision.ALLOW,
            ),
            SecurityControlOutcome(
                control_name="REPLAY_PROTECTION",
                passed=True,
                decision=PolicyDecision.ALLOW,
            ),
            SecurityControlOutcome(
                control_name="NONCE_VALIDATION",
                passed=True,
                decision=PolicyDecision.ALLOW,
            ),
        ],
        decision_trace={"authorization_reference": "auth_test_ref_123"},
    )


def _make_sample_transaction(tx_id: str = "tx_recon_001") -> Transaction:
    return Transaction(
        transaction_id=tx_id,
        merchant_id="merchant_test_1",
        buyer_id="buyer_test_1",
        mandate_id="mandate_test_1",
        amount_paise=50000,
        currency=Currency.INR,
        mandate_version=1,
        policy_version=1,
        cart_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        state=TransactionState.AUTHORIZED,
    )


def _make_proposal(tx_id: str = "tx_recon_001") -> PaymentExecuteProposalRequest:
    return PaymentExecuteProposalRequest(
        transaction_id=tx_id,
        merchant_id="merchant_test_1",
        buyer_id="buyer_test_1",
        mandate_id="mandate_test_1",
        amount_paise=50000,
        currency=Currency.INR,
        cart_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        operation=McpOperation.CREATE_ORDER,
        idempotency_key=f"idem_{tx_id}",
    )


class TestReconciliationMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = MockRazorpayAdapter()
        self.service = PaymentExecutionService(adapter=self.adapter)
        self.auth = _make_allowed_auth_result()

    def test_case_a_pre_dispatch_failure_rolls_back(self) -> None:
        """Case A: Request fails before reaching provider -> FAILED -> ROLLED_BACK."""
        tx = _make_sample_transaction("tx_case_a")
        prop = _make_proposal("tx_case_a")
        self.adapter.set_next_failure(
            category=ExecutionFailureCategory.PROVIDER_REJECTED,
            reason=RejectionReason.METHOD_NOT_AUTHORIZED,
            message="Provider explicitly rejected payment",
        )

        res = self.service.execute_payment(prop, self.auth, tx)

        self.assertFalse(res.success)
        self.assertEqual(res.state, TransactionState.ROLLED_BACK)
        self.assertEqual(res.provider_status, PaymentResultState.FAILED)

    def test_case_b_timeout_initial_executing_reconciles_to_success(self) -> None:
        """Case B: Initial dispatch times out (UNKNOWN/EXECUTING), reconciliation succeeds -> COMMITTED."""
        tx = _make_sample_transaction("tx_case_b")
        prop = _make_proposal("tx_case_b")
        self.adapter.set_simulate_timeout(True)

        # Initial execution attempt times out
        res1 = self.service.execute_payment(prop, self.auth, tx)

        # Invariant checks for UNKNOWN:
        self.assertFalse(res1.success)
        self.assertEqual(res1.state, TransactionState.EXECUTING)
        self.assertEqual(res1.provider_status, PaymentResultState.UNKNOWN)
        self.assertNotEqual(res1.state, TransactionState.ROLLED_BACK)
        self.assertNotEqual(res1.state, TransactionState.COMMITTED)

        # Clear timeout and configure reconciliation status to SUCCESS
        self.adapter.set_simulate_timeout(False)
        self.adapter.set_reconciliation_status(PaymentResultState.SUCCESS)

        # Retry execution (triggers automatic status reconciliation)
        res2 = self.service.execute_payment(prop, self.auth, tx)

        self.assertTrue(res2.success)
        self.assertEqual(res2.state, TransactionState.COMMITTED)
        self.assertEqual(res2.provider_status, PaymentResultState.SUCCESS)
        self.assertEqual(self.adapter.reconciled_requests[0], "tx_case_b")

    def test_case_c_timeout_initial_executing_reconciles_to_failed(self) -> None:
        """Case C: Initial dispatch times out (UNKNOWN/EXECUTING), reconciliation finds failed -> ROLLED_BACK."""
        tx = _make_sample_transaction("tx_case_c")
        prop = _make_proposal("tx_case_c")
        self.adapter.set_simulate_timeout(True)

        res1 = self.service.execute_payment(prop, self.auth, tx)
        self.assertEqual(res1.state, TransactionState.EXECUTING)
        self.assertEqual(res1.provider_status, PaymentResultState.UNKNOWN)

        self.adapter.set_simulate_timeout(False)
        self.adapter.set_reconciliation_status(PaymentResultState.FAILED)

        res2 = self.service.execute_payment(prop, self.auth, tx)

        self.assertFalse(res2.success)
        self.assertEqual(res2.state, TransactionState.ROLLED_BACK)
        self.assertEqual(res2.provider_status, PaymentResultState.FAILED)

    def test_case_d_reconciliation_times_out_remains_executing(self) -> None:
        """Case D: Provider status lookup also times out -> remains EXECUTING with UNKNOWN status."""
        tx = _make_sample_transaction("tx_case_d")
        prop = _make_proposal("tx_case_d")
        self.adapter.set_simulate_timeout(True)

        res1 = self.service.execute_payment(prop, self.auth, tx)
        self.assertEqual(res1.state, TransactionState.EXECUTING)

        self.adapter.set_simulate_timeout(False)
        self.adapter.set_reconciliation_timeout(True)

        res2 = self.service.reconcile_payment_status(tx.transaction_id)

        self.assertFalse(res2.success)
        self.assertEqual(res2.state, TransactionState.EXECUTING)
        self.assertEqual(res2.provider_status, PaymentResultState.UNKNOWN)

    def test_case_e_malformed_reconciliation_remains_executing(self) -> None:
        """Case E: Provider status lookup returns malformed data -> remains EXECUTING with UNKNOWN status."""
        tx = _make_sample_transaction("tx_case_e")
        prop = _make_proposal("tx_case_e")
        self.adapter.set_simulate_timeout(True)

        self.service.execute_payment(prop, self.auth, tx)

        self.adapter.set_simulate_timeout(False)
        self.adapter.set_reconciliation_malformed(True)

        res = self.service.reconcile_payment_status(tx.transaction_id)

        self.assertFalse(res.success)
        self.assertEqual(res.state, TransactionState.EXECUTING)
        self.assertEqual(res.provider_status, PaymentResultState.UNKNOWN)

    def test_case_f_reconciliation_prevents_duplicate_payment_dispatch(self) -> None:
        """Case F: Retry of UNKNOWN outcome uses fetch_payment_status, NOT execute_payment dispatch."""
        tx = _make_sample_transaction("tx_case_f")
        prop = _make_proposal("tx_case_f")

        # 1. Initial timeout
        self.adapter.set_simulate_timeout(True)
        self.service.execute_payment(prop, self.auth, tx)
        self.assertEqual(len(self.adapter.executed_requests), 1)

        # 2. Retry call after timeout is cleared
        self.adapter.set_simulate_timeout(False)
        self.adapter.set_reconciliation_status(PaymentResultState.SUCCESS)

        res2 = self.service.execute_payment(prop, self.auth, tx)

        # Must NOT have made a second execute_payment call on adapter!
        self.assertEqual(len(self.adapter.executed_requests), 1)
        # Must have made a reconcile request
        self.assertEqual(len(self.adapter.reconciled_requests), 1)
        self.assertTrue(res2.success)
        self.assertEqual(res2.state, TransactionState.COMMITTED)


if __name__ == "__main__":
    unittest.main()
