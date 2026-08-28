"""
Multi-threaded Concurrency & Idempotency test suite for S01.11 Payment Execution Boundary.
"""

import concurrent.futures
import unittest

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    Currency,
    McpOperation,
    PaymentResultState,
    PolicyDecision,
    TransactionState,
)


class TestPaymentExecutionConcurrency(unittest.TestCase):
    """Exhaustive multi-threaded concurrency and race-condition test suite for S01.11."""

    def setUp(self) -> None:
        self.adapter = MockRazorpayAdapter()
        self.service = PaymentExecutionService(self.adapter)

        self.transaction_id = "tx-conc-exec-100"
        self.transaction = Transaction(
            transaction_id=self.transaction_id,
            buyer_id="buyer-conc",
            merchant_id="merchant-conc",
            mandate_id="mandate-conc",
            mandate_version=1,
            policy_version=1,
            cart_hash="c" * 64,
            amount_paise=25000,
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
            merchant_id="merchant-conc",
            buyer_id="buyer-conc",
            mandate_id="mandate-conc",
            amount_paise=25000,
            currency=Currency.INR,
            cart_hash="c" * 64,
            operation=McpOperation.CREATE_ORDER,
            idempotency_key=f"exec:{self.transaction_id}",
        )

    # ------------------------------------------------------------------
    # 1. 20 Concurrent Workers for Same Transaction
    # ------------------------------------------------------------------

    def test_20_concurrent_execution_workers_executes_adapter_exactly_once(self) -> None:
        def _worker():
            return self.service.execute_payment(
                proposal=self.proposal,
                authorization_result=self.auth_allow,
                transaction=self.transaction,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_worker) for _ in range(20)]
            results = [f.result() for f in futures]

        # All 20 workers get a successful result
        successful_count = sum(1 for r in results if r.success)
        self.assertEqual(successful_count, 20)

        # Exactly 1 result is the initial execution, 19 are idempotent replays
        initial_count = sum(1 for r in results if not r.idempotent_replay)
        replay_count = sum(1 for r in results if r.idempotent_replay)
        self.assertEqual(initial_count, 1)
        self.assertEqual(replay_count, 19)

        # Confirm adapter received exactly ONE call
        self.assertEqual(len(self.adapter.executed_requests), 1)

    # ------------------------------------------------------------------
    # 2. 50 Mixed Concurrent Workers Across 10 Unique Transactions
    # ------------------------------------------------------------------

    def test_50_mixed_concurrent_workers_preserves_single_execution_per_transaction(self) -> None:
        txs = [
            Transaction(
                transaction_id=f"tx-mix-{i}",
                buyer_id="buyer-conc",
                merchant_id="merchant-conc",
                mandate_id="mandate-conc",
                mandate_version=1,
                policy_version=1,
                cart_hash="c" * 64,
                amount_paise=10000 + i * 100,
                currency=Currency.INR,
                state=TransactionState.AUTHORIZED,
            )
            for i in range(10)
        ]

        proposals = [
            PaymentExecuteProposalRequest(
                transaction_id=tx.transaction_id,
                merchant_id=tx.merchant_id,
                buyer_id=tx.buyer_id,
                mandate_id=tx.mandate_id,
                amount_paise=tx.amount_paise,
                currency=tx.currency,
                cart_hash=tx.cart_hash or ("c" * 64),
                operation=McpOperation.CREATE_ORDER,
                idempotency_key=f"exec:{tx.transaction_id}",
            )
            for tx in txs
        ]

        pool = list(zip(txs, proposals)) * 5  # 50 total tasks (5 per transaction)

        def _worker(pair):
            tx, prop = pair
            return self.service.execute_payment(
                proposal=prop,
                authorization_result=self.auth_allow,
                transaction=tx,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(_worker, p) for p in pool]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 50)
        self.assertTrue(all(r.success for r in results))

        # Exactly 10 calls reached the adapter
        self.assertEqual(len(self.adapter.executed_requests), 10)

    # ------------------------------------------------------------------
    # 3. 20 Concurrent Workers During Timeout & Status Reconciliation
    # ------------------------------------------------------------------

    def test_20_concurrent_workers_during_timeout_triggers_reconciliation_safely(self) -> None:
        self.adapter.set_simulate_timeout(True)
        self.adapter.set_reconciliation_timeout(True)

        def _worker_initial():
            return self.service.execute_payment(
                proposal=self.proposal,
                authorization_result=self.auth_allow,
                transaction=self.transaction,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_worker_initial) for _ in range(20)]
            results = [f.result() for f in futures]

        # All initial workers get EXECUTING state with UNKNOWN status
        self.assertEqual(len(results), 20)
        self.assertTrue(all(r.state == TransactionState.EXECUTING for r in results))
        self.assertTrue(all(r.provider_status == PaymentResultState.UNKNOWN for r in results))

        # Exactly 1 call was dispatched to adapter
        self.assertEqual(len(self.adapter.executed_requests), 1)

        # Clear timeout and configure reconciliation status to SUCCESS
        self.adapter.set_simulate_timeout(False)
        self.adapter.set_reconciliation_timeout(False)
        self.adapter.set_reconciliation_status(PaymentResultState.SUCCESS)

        def _worker_retry():
            return self.service.execute_payment(
                proposal=self.proposal,
                authorization_result=self.auth_allow,
                transaction=self.transaction,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(_worker_retry) for _ in range(20)]
            retry_results = [f.result() for f in futures]

        # All retry workers get COMMITTED state with SUCCESS status
        self.assertEqual(len(retry_results), 20)
        self.assertTrue(all(r.state == TransactionState.COMMITTED for r in retry_results))
        self.assertTrue(all(r.provider_status == PaymentResultState.SUCCESS for r in retry_results))

        # Adapter still has only 1 execution call, and exactly 1 reconciliation call
        self.assertEqual(len(self.adapter.executed_requests), 1)
        self.assertGreaterEqual(len(self.adapter.reconciled_requests), 1)


if __name__ == "__main__":
    unittest.main()
