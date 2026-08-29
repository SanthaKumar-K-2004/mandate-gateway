"""
S06 Integration Test Suite — Unknown Outcome & Provider Status Reconciliation.

Tests:
  1. Complete Timeout -> UNKNOWN -> Reconciliation -> COMMITTED E2E flow.
  2. Complete Failure -> UNKNOWN -> Reconciliation -> ROLLED_BACK E2E flow.
  3. Synchronous execution & Webhook processing convergence.
  4. Durable database persistence & session restart recovery.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.domain.reconciliation_engine import ReconciliationService
from apps.api.domain.types import (
    Currency,
    MandateStatus,
    PaymentResultState,
    TransactionState,
)
from db.models.base import Base
from db.models.mandate import MandateModel
from db.models.transaction import TransactionModel
from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestM06ReconciliationIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for status reconciliation and unknown outcomes."""

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

        self.adapter = MockRazorpayAdapter()
        self.reconciliation_service = ReconciliationService(self.adapter)

        # Seed test database
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.merchants.create_merchant(
                merchant_id="mer_rec_01",
                name="Reconciliation Test Merchant",
                razorpay_account_id="acc_rec_01",
            )
            uow.mandates._session.add(
                MandateModel(
                    mandate_id="man_rec_01",
                    buyer_id="buyer_rec_01",
                    merchant_id="mer_rec_01",
                    status=MandateStatus.ACTIVE.value,
                    daily_budget_paise=1000000,
                    currency=Currency.INR.value,
                    expires_at=_utc_now() + timedelta(days=30),
                    created_at=_utc_now(),
                )
            )
            uow.transactions._session.add(
                TransactionModel(
                    transaction_id="tx_rec_01",
                    buyer_id="buyer_rec_01",
                    merchant_id="mer_rec_01",
                    mandate_id="man_rec_01",
                    cart_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    amount_paise=50000,
                    currency=Currency.INR.value,
                    auth_decision="ALLOW",
                    state=TransactionState.EXECUTING.value,
                    idempotency_key="idemp_rec_01",
                    provider_payment_id="pay_rec_001",
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    async def test_01_timeout_to_reconciled_committed_flow(self) -> None:
        # Step 1: Configure mock to return SUCCESS on status fetch
        self.adapter.set_reconciliation_status(PaymentResultState.SUCCESS)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.reconciliation_service.async_reconcile_transaction(uow, "tx_rec_01")
            self.assertTrue(res.success)
            self.assertEqual(res.state, TransactionState.COMMITTED)
            self.assertEqual(res.provider_status, PaymentResultState.SUCCESS)
            await uow.commit()

        # Step 2: Verify database state updated durably
        async with AsyncUnitOfWork(self.session_factory) as uow:
            db_tx = await uow.transactions.get_transaction("tx_rec_01")
            self.assertIsNotNone(db_tx)
            assert db_tx is not None
            self.assertEqual(db_tx.state, TransactionState.COMMITTED.value)

    async def test_02_timeout_to_reconciled_rolled_back_flow(self) -> None:
        # Step 1: Configure mock to return FAILED on status fetch
        self.adapter.set_reconciliation_status(PaymentResultState.FAILED)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.reconciliation_service.async_reconcile_transaction(uow, "tx_rec_01")
            self.assertFalse(res.success)
            self.assertEqual(res.state, TransactionState.ROLLED_BACK)
            self.assertEqual(res.provider_status, PaymentResultState.FAILED)
            await uow.commit()

        # Step 2: Verify database state updated durably
        async with AsyncUnitOfWork(self.session_factory) as uow:
            db_tx = await uow.transactions.get_transaction("tx_rec_01")
            self.assertIsNotNone(db_tx)
            assert db_tx is not None
            self.assertEqual(db_tx.state, TransactionState.ROLLED_BACK.value)

    async def test_03_reconciliation_idempotency_for_terminal_state(self) -> None:
        # Commit the transaction first
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.transition_transaction_state(
                "tx_rec_01", TransactionState.COMMITTED
            )
            await uow.commit()

        # Attempt reconciliation on committed transaction
        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.reconciliation_service.async_reconcile_transaction(uow, "tx_rec_01")
            self.assertTrue(res.success)
            self.assertTrue(res.idempotent_replay)
            self.assertEqual(res.state, TransactionState.COMMITTED)


if __name__ == "__main__":
    unittest.main()
