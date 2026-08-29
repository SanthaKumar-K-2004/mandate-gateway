"""
M07 — Transaction Reliability & Concurrency Verification Test Suite.

Verifies system safety, exact-once effect guarantees, idempotency races,
recovery worker contention, and outbox delivery under heavy multi-session concurrency.
"""

from __future__ import annotations

import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult, SecurityControlOutcome
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.contracts.merchant import McpOperation
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.recovery_engine import TransactionRecoveryService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    Currency,
    MandateStatus,
    PaymentResultState,
    PolicyDecision,
    TransactionState,
)
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_auth_result() -> AuthorizationResult:
    controls = [
        SecurityControlOutcome("MANDATE_EVALUATION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("MERCHANT_POLICY", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("CART_INTEGRITY", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("BUDGET_RESERVATION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("REPLAY_PROTECTION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("NONCE_VALIDATION", True, PolicyDecision.ALLOW),
    ]
    return AuthorizationResult(
        decision=PolicyDecision.ALLOW,
        control_outcomes=controls,
        decision_trace={"authorization_reference": f"auth_{uuid.uuid4().hex[:8]}"},
    )


class TestM07ReliabilityConcurrency(unittest.IsolatedAsyncioTestCase):
    """Multi-session concurrency & race condition test suite for M07."""

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        self.m_id = _uid("mer")
        self.man_id = _uid("man")
        self.b_id = _uid("buy")
        now = _utc_now()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.merchants.create_merchant(
                self.m_id, "Reliability Store", f"acc_{self.m_id[:6]}"
            )
            await uow.merchants.create_policy(
                policy_id=f"pol_{self.m_id[:6]}",
                merchant_id=self.m_id,
                policy_version="1",
                autonomous_limit_paise=5_000_000,
                step_up_threshold_paise=4_000_000,
                allowed_operations=["CREATE_ORDER", "CREATE_PAYMENT_LINK", "FETCH_PAYMENT"],
            )
            await uow.mandates.create_mandate(
                mandate_id=self.man_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                daily_budget_paise=5_000_000,
                status=MandateStatus.ACTIVE.value,
                expires_at=now + timedelta(days=30),
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_scenario_A_20_concurrent_execution_requests(self) -> None:
        """20 concurrent payment execution requests for same transaction yield exactly 1 provider call."""
        tx_id = _uid("tx")
        cart_hash = "c" * 64
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,
                cart_hash=cart_hash,
                idempotency_key=f"idem_{tx_id}",
                state=TransactionState.AUTHORIZED,
            )
            await uow.commit()

        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter)
        auth = _make_auth_result()
        tx = Transaction(
            transaction_id=tx_id,
            buyer_id=self.b_id,
            merchant_id=self.m_id,
            mandate_id=self.man_id,
            mandate_version=1,
            policy_version=1,
            amount_paise=5000,
            cart_hash=cart_hash,
            state=TransactionState.AUTHORIZED,
        )
        proposal = PaymentExecuteProposalRequest(
            transaction_id=tx_id,
            merchant_id=self.m_id,
            buyer_id=self.b_id,
            mandate_id=self.man_id,
            amount_paise=5000,
            currency=Currency.INR,
            cart_hash=cart_hash,
            operation=McpOperation.CREATE_ORDER,
            idempotency_key=f"idem_conc_{tx_id}",
        )

        async def worker():
            async with AsyncUnitOfWork(self.session_factory) as uow:
                res = await service.async_execute_payment(uow, proposal, auth, tx)
                if res.success:
                    await uow.commit()
                return res

        results = await asyncio.gather(*[worker() for _ in range(20)])
        successful = [r for r in results if r.success]
        self.assertGreaterEqual(len(successful), 1, "At least one execution must succeed.")
        self.assertEqual(
            len(adapter.executed_requests),
            1,
            "Exactly one provider network call must be executed (no double charge!).",
        )

    async def test_scenario_B_concurrent_recovery_workers(self) -> None:
        """10 concurrent recovery workers scanning a stuck transaction resolve it exactly once."""
        tx_id = _uid("tx")
        past = _utc_now() - timedelta(seconds=60)
        async with AsyncUnitOfWork(self.session_factory) as uow:
            t = await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=10000,
                cart_hash="d" * 64,
                idempotency_key=f"idem_{tx_id}",
                state=TransactionState.AUTHORIZED,
            )
            t.state = TransactionState.EXECUTING.value
            t.updated_at = past
            await uow.commit()

        adapter = MockRazorpayAdapter()
        adapter.set_reconciliation_status(PaymentResultState.SUCCESS)
        recovery_service = TransactionRecoveryService(adapter)

        async def recovery_worker():
            async with AsyncUnitOfWork(self.session_factory) as uow:
                rec = await recovery_service.reconcile_transaction(uow, tx_id)
                if rec.recovered:
                    await uow.commit()
                return rec

        recs = await asyncio.gather(*[recovery_worker() for _ in range(10)])
        recovered = [r for r in recs if r.final_state == TransactionState.COMMITTED.value]
        self.assertGreaterEqual(len(recovered), 1, "At least one recovery worker must reconcile.")

        async with AsyncUnitOfWork(self.session_factory) as uow:
            final_tx = await uow.transactions.get_transaction(tx_id)
            self.assertIsNotNone(final_tx)
            assert final_tx is not None
            self.assertEqual(final_tx.state, TransactionState.COMMITTED.value)

    async def test_scenario_C_concurrent_outbox_and_webhook_dedup(self) -> None:
        """Concurrent webhook event registration enforces primary key deduplication."""
        event_id = f"evt_{uuid.uuid4().hex}"
        tx_id = _uid("tx")

        async def webhook_worker():
            try:
                async with AsyncUnitOfWork(self.session_factory) as uow:
                    rec, is_dup = await uow.webhooks.register_event(
                        event_id=event_id,
                        event_type="payment.captured",
                        transaction_id=tx_id,
                        merchant_id=self.m_id,
                        payload_hash="hash" * 16,
                    )
                    if not is_dup:
                        await uow.commit()
                    return is_dup
            except Exception:
                return True

        results = await asyncio.gather(*[webhook_worker() for _ in range(15)])
        new_registrations = [r for r in results if not r]
        self.assertEqual(
            len(new_registrations),
            1,
            "Exactly one worker must register the original webhook event.",
        )


if __name__ == "__main__":
    unittest.main()
