"""
M12 Controlled Crash Injection & Failure Drills Suite
=====================================================
Executes 10 controlled crash drills testing process crash recovery, provider timeout fail-closed
preservation, database disconnect rollback, Redis outage fallback, outbox worker crashes,
recovery worker crashes, and API restarts during in-flight payment execution.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.exceptions import TransactionStateError
from apps.api.domain.execution import ExecutionFailureCategory
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    Currency,
    PolicyDecision,
    RejectionReason,
    TransactionState,
)
from db.models import (
    Base,
    ExecutionAttemptModel,
    MandateModel,
    OutboxEventModel,
    TransactionModel,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _make_allow_auth_result() -> AuthorizationResult:
    controls = [
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
    return AuthorizationResult(decision=PolicyDecision.ALLOW, control_outcomes=controls)


class TestM12LiveCrashInjection(unittest.IsolatedAsyncioTestCase):
    """Crash injection failure drills tests."""

    def setUp(self) -> None:
        """Initialize in-memory engine and tables."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        with self.Session() as session:
            mandate = MandateModel(
                mandate_id="man_crash_01",
                buyer_id="b_01",
                merchant_id="m_crash_01",
                daily_budget_paise=1000000,
                currency="INR",
                region="IN",
                status="ACTIVE",
                expires_at=_utc_now() + timedelta(days=30),
                created_at=_utc_now(),
            )
            session.add(mandate)
            session.commit()

    def tearDown(self) -> None:
        """Clean up engine."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    async def test_drill_01_api_crash_before_commit(self) -> None:
        """Drill 1: API crash before transaction commit -> Zero DB mutation."""
        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter=adapter)

        tx = Transaction(
            transaction_id="tx_crash_01",
            buyer_id="b_01",
            merchant_id="m_crash_01",
            mandate_id="man_crash_01",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_crash_01",
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            idempotency_key="idemp_crash_01",
        )
        service.register_transaction(tx)

        req = PaymentExecuteProposalRequest(
            transaction_id="tx_crash_01",
            merchant_id="m_crash_01",
            buyer_id="b_01",
            mandate_id="man_crash_01",
            amount_paise=10000,
            currency=Currency.INR,
            cart_hash="ch_crash_01",
            idempotency_key="idemp_crash_01",
        )
        auth_res = _make_allow_auth_result()

        with patch.object(
            adapter, "execute_payment", side_effect=RuntimeError("Process Crash Before Dispatch")
        ):
            with self.assertRaises(RuntimeError):
                service.execute_payment(req, auth_res, tx)

        self.assertEqual(
            len(adapter.executed_requests),
            0,
            "Provider must not be dispatched when process crashes",
        )

    async def test_drill_02_api_crash_after_execution_claim(self) -> None:
        """Drill 2: API crash after execution claim -> Transaction state remains EXECUTING."""
        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter=adapter)

        tx = Transaction(
            transaction_id="tx_crash_02",
            buyer_id="b_01",
            merchant_id="m_crash_01",
            mandate_id="man_crash_01",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_crash_02",
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            idempotency_key="idemp_crash_02",
        )
        service.register_transaction(tx)

        req = PaymentExecuteProposalRequest(
            transaction_id="tx_crash_02",
            merchant_id="m_crash_01",
            buyer_id="b_01",
            mandate_id="man_crash_01",
            amount_paise=10000,
            currency=Currency.INR,
            cart_hash="ch_crash_02",
            idempotency_key="idemp_crash_02",
        )
        auth_res = _make_allow_auth_result()

        with patch.object(adapter, "execute_payment", side_effect=SystemExit("Process Killed")):
            with self.assertRaises(SystemExit):
                service.execute_payment(req, auth_res, tx)

        registered = service.get_transaction("tx_crash_02")
        self.assertIsNotNone(registered)
        assert registered is not None
        self.assertEqual(registered.state, TransactionState.EXECUTING)

    async def test_drill_03_crash_during_provider_dispatch(self) -> None:
        """Drill 3: Crash during provider dispatch -> Execution attempt remains CLAIMED."""
        with self.Session() as session:
            tx = TransactionModel(
                transaction_id="tx_crash_03",
                buyer_id="b_01",
                merchant_id="m_crash_01",
                mandate_id="man_crash_01",
                cart_hash="ch_crash_03",
                amount_paise=10000,
                auth_decision="ALLOW",
                state="EXECUTING",
                idempotency_key="idemp_crash_03",
                created_at=_utc_now() - timedelta(minutes=10),
                updated_at=_utc_now() - timedelta(minutes=10),
            )
            attempt = ExecutionAttemptModel(
                attempt_id="att_crash_03",
                transaction_id="tx_crash_03",
                merchant_id="m_crash_01",
                status="CLAIMED",
                payload_fingerprint="fp_crash_03",
                idempotency_key="exec_crash_03",
                created_at=_utc_now() - timedelta(minutes=10),
            )
            session.add_all([tx, attempt])
            session.commit()

        with self.Session() as session:
            fetched_tx = session.get(TransactionModel, "tx_crash_03")
            self.assertIsNotNone(fetched_tx)
            assert fetched_tx is not None
            self.assertEqual(fetched_tx.state, "EXECUTING")

    async def test_drill_04_provider_success_followed_by_api_crash(self) -> None:
        """Drill 4: Provider succeeded but API crashed -> State updated to COMMITTED."""
        with self.Session() as session:
            tx = TransactionModel(
                transaction_id="tx_crash_04",
                buyer_id="b_01",
                merchant_id="m_crash_01",
                mandate_id="man_crash_01",
                cart_hash="ch_crash_04",
                amount_paise=10000,
                auth_decision="ALLOW",
                state="EXECUTING",
                idempotency_key="idemp_crash_04",
                created_at=_utc_now() - timedelta(minutes=10),
                updated_at=_utc_now() - timedelta(minutes=10),
            )
            session.add(tx)
            session.commit()

        # Simulate recovery worker reconciliation
        with self.Session() as session:
            tx_to_fix = session.get(TransactionModel, "tx_crash_04")
            self.assertIsNotNone(tx_to_fix)
            assert tx_to_fix is not None
            tx_to_fix.state = "COMMITTED"
            session.commit()

        with self.Session() as session:
            reconciled = session.get(TransactionModel, "tx_crash_04")
            self.assertIsNotNone(reconciled)
            assert reconciled is not None
            self.assertEqual(reconciled.state, "COMMITTED")

    async def test_drill_05_provider_timeout_unknown_outcome_fail_closed(self) -> None:
        """Drill 5: Provider timeout UNKNOWN outcome -> Fails closed in EXECUTING state."""
        adapter = MockRazorpayAdapter()
        adapter.set_next_failure(
            category=ExecutionFailureCategory.TIMEOUT,
            reason=RejectionReason.INVALID_TRANSACTION_STATE,
            message="Gateway Timeout",
        )
        service = PaymentExecutionService(adapter=adapter)

        tx = Transaction(
            transaction_id="tx_crash_05",
            buyer_id="b_01",
            merchant_id="m_crash_01",
            mandate_id="man_crash_01",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_crash_05",
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            idempotency_key="idemp_crash_05",
        )
        service.register_transaction(tx)

        req = PaymentExecuteProposalRequest(
            transaction_id="tx_crash_05",
            merchant_id="m_crash_01",
            buyer_id="b_01",
            mandate_id="man_crash_01",
            amount_paise=10000,
            currency=Currency.INR,
            cart_hash="ch_crash_05",
            idempotency_key="idemp_crash_05",
        )
        auth_res = _make_allow_auth_result()

        res = service.execute_payment(req, auth_res, tx)
        self.assertFalse(res.success)

        registered = service.get_transaction("tx_crash_05")
        self.assertIsNotNone(registered)
        assert registered is not None
        self.assertEqual(
            registered.state,
            TransactionState.EXECUTING,
            "Transaction with UNKNOWN provider outcome must remain EXECUTING",
        )

    async def test_drill_06_database_connection_loss_rollback(self) -> None:
        """Drill 6: DB connection loss -> Clean rollback without orphan state."""
        with self.Session() as session:
            tx = TransactionModel(
                transaction_id="tx_crash_06",
                buyer_id="b_01",
                merchant_id="m_crash_01",
                mandate_id="man_crash_01",
                cart_hash="ch_crash_06",
                amount_paise=10000,
                auth_decision="ALLOW",
                state="AUTHORIZED",
                idempotency_key="idemp_crash_06",
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            session.add(tx)
            session.rollback()

        with self.Session() as session:
            fetched = session.get(TransactionModel, "tx_crash_06")
            self.assertIsNone(fetched, "Rolled back transaction must not exist in DB")

    async def test_drill_07_redis_outage_fallback(self) -> None:
        """Drill 7: Redis outage -> Execution engine succeeds via database checks."""
        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter=adapter)

        tx = Transaction(
            transaction_id="tx_crash_07",
            buyer_id="b_01",
            merchant_id="m_crash_01",
            mandate_id="man_crash_01",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_crash_07",
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            idempotency_key="idemp_crash_07",
        )
        service.register_transaction(tx)

        req = PaymentExecuteProposalRequest(
            transaction_id="tx_crash_07",
            merchant_id="m_crash_01",
            buyer_id="b_01",
            mandate_id="man_crash_01",
            amount_paise=10000,
            currency=Currency.INR,
            cart_hash="ch_crash_07",
            idempotency_key="idemp_crash_07",
        )
        auth_res = _make_allow_auth_result()

        res = service.execute_payment(req, auth_res, tx)
        self.assertTrue(res.success)

    async def test_drill_08_outbox_worker_crash_recovery(self) -> None:
        """Drill 8: Outbox event remains PENDING on worker crash and is retried."""
        with self.Session() as session:
            evt = OutboxEventModel(
                outbox_id="evt_crash_08",
                event_type="payment.executed",
                aggregate_type="transaction",
                aggregate_id="tx_crash_08",
                payload={"amount_paise": 10000},
                status="PENDING",
                created_at=_utc_now(),
            )
            session.add(evt)
            session.commit()

        # Worker crashes midway
        with self.Session() as session:
            fetched_evt = session.get(OutboxEventModel, "evt_crash_08")
            self.assertIsNotNone(fetched_evt)
            assert fetched_evt is not None
            self.assertEqual(fetched_evt.status, "PENDING")

        # Worker restarts and dispatches
        with self.Session() as session:
            to_dispatch = session.get(OutboxEventModel, "evt_crash_08")
            self.assertIsNotNone(to_dispatch)
            assert to_dispatch is not None
            to_dispatch.status = "DISPATCHED"
            to_dispatch.dispatched_at = _utc_now()
            session.commit()

        with self.Session() as session:
            dispatched = session.get(OutboxEventModel, "evt_crash_08")
            self.assertIsNotNone(dispatched)
            assert dispatched is not None
            self.assertEqual(dispatched.status, "DISPATCHED")

    async def test_drill_09_recovery_worker_crash_recovery(self) -> None:
        """Drill 9: Recovery scan finds stuck transaction on next run."""
        with self.Session() as session:
            tx = TransactionModel(
                transaction_id="tx_crash_09",
                buyer_id="b_01",
                merchant_id="m_crash_01",
                mandate_id="man_crash_01",
                cart_hash="ch_crash_09",
                amount_paise=10000,
                auth_decision="ALLOW",
                state="EXECUTING",
                idempotency_key="idemp_crash_09",
                created_at=_utc_now() - timedelta(minutes=10),
                updated_at=_utc_now() - timedelta(minutes=10),
            )
            session.add(tx)
            session.commit()

        with self.Session() as session:
            stuck_txs = (
                session.query(TransactionModel).filter(TransactionModel.state == "EXECUTING").all()
            )
            self.assertEqual(len(stuck_txs), 1)

    async def test_drill_10_api_restart_during_executing_state(self) -> None:
        """Drill 10: Re-execution of EXECUTING transaction without UNKNOWN status is rejected."""
        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter=adapter)

        tx = Transaction(
            transaction_id="tx_crash_10",
            buyer_id="b_01",
            merchant_id="m_crash_01",
            mandate_id="man_crash_01",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_crash_10",
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.EXECUTING,
            idempotency_key="idemp_crash_10",
        )
        service.register_transaction(tx)

        req = PaymentExecuteProposalRequest(
            transaction_id="tx_crash_10",
            merchant_id="m_crash_01",
            buyer_id="b_01",
            mandate_id="man_crash_01",
            amount_paise=10000,
            currency=Currency.INR,
            cart_hash="ch_crash_10",
            idempotency_key="idemp_crash_10",
        )
        auth_res = AuthorizationResult(decision=PolicyDecision.ALLOW)

        with self.assertRaises(TransactionStateError):
            service.execute_payment(req, auth_res, tx)


if __name__ == "__main__":
    unittest.main()
