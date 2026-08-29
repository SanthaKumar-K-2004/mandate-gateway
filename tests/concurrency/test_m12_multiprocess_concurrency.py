"""
M12 True Multi-Process Concurrency Verification Suite
=====================================================
Validates payment safety, budget overspend prevention, single-use nonces,
recovery reconciliation, and outbox event publishing across multiple OS processes.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import Currency, PolicyDecision, TransactionState
from db.models import (
    Base,
    MandateModel,
    NonceRecordModel,
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


def _worker_execute_payment(
    db_url: str, tx_id: str, idempotency_key: str
) -> dict[str, str | int | bool]:
    """Execute payment proposal in an independent worker process."""
    engine = create_engine(db_url, echo=False)
    adapter = MockRazorpayAdapter()
    service = PaymentExecutionService(adapter=adapter)

    # Register transaction
    tx = Transaction(
        transaction_id=tx_id,
        buyer_id="b_01",
        merchant_id="m_mp_01",
        mandate_id="man_mp_01",
        mandate_version=1,
        policy_version=1,
        cart_hash="ch_01",
        amount_paise=10000,
        currency=Currency.INR,
        state=TransactionState.AUTHORIZED,
        idempotency_key=idempotency_key,
    )
    service.register_transaction(tx)

    req = PaymentExecuteProposalRequest(
        transaction_id=tx_id,
        merchant_id="m_mp_01",
        buyer_id="b_01",
        mandate_id="man_mp_01",
        amount_paise=10000,
        currency=Currency.INR,
        cart_hash="ch_01",
        idempotency_key=idempotency_key,
    )
    auth_res = _make_allow_auth_result()

    try:
        res = service.execute_payment(req, auth_res, tx)
        return {
            "success": res.success,
            "provider_payment_id": res.external_reference or "",
            "adapter_calls": len(adapter.executed_requests),
        }
    finally:
        engine.dispose()


def _worker_consume_nonce(db_url: str, nonce_str: str, merchant_id: str) -> bool:
    """Attempt single-use nonce consumption in an independent worker process."""
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    success = False
    try:
        with Session() as session:
            nonce_obj = NonceRecordModel(
                nonce=nonce_str,
                transaction_id="tx_01",
                mandate_id="man_01",
                status="CONSUMED",
                created_at=_utc_now(),
                consumed_at=_utc_now(),
            )
            session.add(nonce_obj)
            session.commit()
            success = True
    except Exception:
        success = False
    finally:
        engine.dispose()
    return success


def _worker_reserve_budget(db_url: str, mandate_id: str, amount_paise: int) -> bool:
    """Attempt budget reservation in an independent worker process."""
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    reserved = False
    try:
        with Session() as session:
            mandate = session.get(MandateModel, mandate_id)
            if mandate and mandate.daily_budget_paise >= amount_paise:
                mandate.daily_budget_paise -= amount_paise
                session.commit()
                reserved = True
            else:
                session.rollback()
                reserved = False
    except Exception:
        reserved = False
    finally:
        engine.dispose()
    return reserved


def _worker_reconcile_transaction(db_url: str, tx_id: str) -> bool:
    """Simulate recovery worker reconciliation in an independent process."""
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    reconciled = False
    try:
        with Session() as session:
            tx = session.get(TransactionModel, tx_id)
            if tx and tx.state == "EXECUTING":
                tx.state = "COMMITTED"
                session.commit()
                reconciled = True
    except Exception:
        reconciled = False
    finally:
        engine.dispose()
    return reconciled


def _worker_publish_outbox(db_url: str, outbox_id: str) -> bool:
    """Simulate publishing outbox event in an independent process."""
    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)
    published = False
    try:
        with Session() as session:
            evt = session.get(OutboxEventModel, outbox_id)
            if evt and evt.status == "PENDING":
                evt.status = "DISPATCHED"
                evt.dispatched_at = _utc_now()
                session.commit()
                published = True
    except Exception:
        published = False
    finally:
        engine.dispose()
    return published


class TestM12MultiProcessConcurrency(unittest.TestCase):
    """Multi-process concurrency verification tests."""

    def setUp(self) -> None:
        """Create shared sqlite file engine for multi-process access."""
        self.db_path = f"/tmp/m12_mp_test_{os.getpid()}.db"
        self.db_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        """Clean up shared test database file."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_MP01_duplicate_payment_requests_multiprocess(self) -> None:
        """Scenario MP01: 20 independent processes target the same payment transaction."""
        tx_id = "tx_mp01_duplicate"
        idemp_key = "idemp_mp01_dup"

        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(_worker_execute_payment, self.db_url, tx_id, idemp_key)
                for _ in range(20)
            ]
            results = [f.result() for f in futures]

        successes = [r["success"] for r in results]
        provider_ids = [r["provider_payment_id"] for r in results]

        self.assertTrue(all(successes), f"All execution requests must succeed: {successes}")
        self.assertEqual(
            len(set(provider_ids)), 1, "All responses must return the same provider payment ID"
        )

    def test_MP02_budget_race_multiprocess(self) -> None:
        """Scenario MP02: 20 worker processes attempt budget reservation concurrently."""
        with self.Session() as session:
            mandate = MandateModel(
                mandate_id="man_mp02_budget",
                buyer_id="b_01",
                merchant_id="m_mp_01",
                daily_budget_paise=50000,  # 500 INR in paise
                currency="INR",
                region="IN",
                status="ACTIVE",
                expires_at=_utc_now() + timedelta(days=30),
                created_at=_utc_now(),
            )
            session.add(mandate)
            session.commit()

        # 20 workers each try to reserve 10000 paise (Max budget is 50000 paise => max 5 can succeed)
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(_worker_reserve_budget, self.db_url, "man_mp02_budget", 10000)
                for _ in range(20)
            ]
            results = [f.result() for f in futures]

        success_count = sum(1 for r in results if r)
        self.assertLessEqual(
            success_count, 5, "Success count must not exceed maximum budget capacity"
        )

        with self.Session() as session:
            mandate_after = session.get(MandateModel, "man_mp02_budget")
            self.assertIsNotNone(mandate_after)
            assert mandate_after is not None
            self.assertGreaterEqual(
                mandate_after.daily_budget_paise, 0, "Remaining daily budget must never go negative"
            )

    def test_MP03_nonce_race_multiprocess(self) -> None:
        """Scenario MP03: 20 worker processes consume the same nonce concurrently."""
        nonce_val = "nonce_mp03_race"

        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(_worker_consume_nonce, self.db_url, nonce_val, "m_mp_01")
                for _ in range(20)
            ]
            results = [f.result() for f in futures]

        successes = sum(1 for r in results if r)
        failures = sum(1 for r in results if not r)

        self.assertEqual(successes, 1, "Exactly 1 process must consume the nonce successfully")
        self.assertEqual(failures, 19, "Exactly 19 processes must fail nonce consumption")

    def test_MP04_recovery_race_multiprocess(self) -> None:
        """Scenario MP04: Multiple recovery workers reconcile the same EXECUTING transaction."""
        with self.Session() as session:
            tx = TransactionModel(
                transaction_id="tx_mp04_rec",
                buyer_id="b_01",
                merchant_id="m_mp_01",
                mandate_id="man_mp_01",
                cart_hash="ch_mp04",
                amount_paise=10000,
                auth_decision="ALLOW",
                state="EXECUTING",
                idempotency_key="idemp_mp04_rec",
                created_at=_utc_now() - timedelta(minutes=10),
                updated_at=_utc_now() - timedelta(minutes=10),
            )
            session.add(tx)
            session.commit()

        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(_worker_reconcile_transaction, self.db_url, "tx_mp04_rec")
                for _ in range(4)
            ]
            results = [f.result() for f in futures]

        reconciled_count = sum(1 for r in results if r)
        self.assertEqual(
            reconciled_count, 1, "Exactly 1 recovery worker process must reconcile the transaction"
        )

    def test_MP05_outbox_race_multiprocess(self) -> None:
        """Scenario MP05: Multiple outbox workers publish pending events concurrently."""
        with self.Session() as session:
            for i in range(5):
                evt = OutboxEventModel(
                    outbox_id=f"evt_mp05_{i}",
                    event_type="payment.executed",
                    aggregate_type="transaction",
                    aggregate_id=f"tx_mp05_{i}",
                    payload={"amount_paise": 10000},
                    status="PENDING",
                    created_at=_utc_now(),
                )
                session.add(evt)
            session.commit()

        with ProcessPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_worker_publish_outbox, self.db_url, f"evt_mp05_{i}")
                for i in range(5)
            ]
            results = [f.result() for f in futures]

        total_published = sum(1 for r in results if r)
        self.assertEqual(total_published, 5, "All 5 outbox events must be published cleanly")


if __name__ == "__main__":
    unittest.main()
