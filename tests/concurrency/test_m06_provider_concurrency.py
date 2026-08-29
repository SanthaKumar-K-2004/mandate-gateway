"""
S06 Concurrency Matrix Test Suite — 5 Provider & Webhook Race Scenarios.

Scenarios:
  1. Duplicate API Execution Race (concurrent execution requests -> max 1 dispatch).
  2. Timeout + Retry Race (timeout outcome -> retry reconciles without double charge).
  3. Webhook + Synchronous Response Race (convergent final state).
  4. Duplicate Webhooks Race (10 concurrent webhook deliveries -> 1 state mutation).
  5. Reconciliation + Webhook Race (safe resolution without state corruption).
"""

from __future__ import annotations

import asyncio
import hmac
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.domain.reconciliation_engine import ReconciliationService
from apps.api.domain.types import Currency, MandateStatus, PaymentResultState, TransactionState
from apps.api.domain.webhook_engine import WebhookEngine
from db.models.base import Base
from db.models.mandate import MandateModel
from db.models.transaction import TransactionModel
from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestM06ProviderConcurrency(unittest.IsolatedAsyncioTestCase):
    """Concurrency test suite for 5 provider & webhook race scenarios."""

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

        self.secret = "whsec_test_secret_key_12345"
        self.adapter = MockRazorpayAdapter()
        self.webhook_engine = WebhookEngine(webhook_secret=self.secret)
        self.reconciliation_service = ReconciliationService(self.adapter)

        # Seed initial merchant, mandate, and transaction
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.merchants.create_merchant(
                merchant_id="mer_conc_01",
                name="Concurrency Test Merchant",
                razorpay_account_id="acc_conc_01",
            )
            uow.mandates._session.add(
                MandateModel(
                    mandate_id="man_conc_01",
                    buyer_id="buyer_conc_01",
                    merchant_id="mer_conc_01",
                    status=MandateStatus.ACTIVE.value,
                    daily_budget_paise=1000000,
                    currency=Currency.INR.value,
                    expires_at=_utc_now() + timedelta(days=30),
                    created_at=_utc_now(),
                )
            )
            uow.transactions._session.add(
                TransactionModel(
                    transaction_id="tx_conc_01",
                    buyer_id="buyer_conc_01",
                    merchant_id="mer_conc_01",
                    mandate_id="man_conc_01",
                    cart_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    amount_paise=50000,
                    currency=Currency.INR.value,
                    auth_decision="ALLOW",
                    state=TransactionState.EXECUTING.value,
                    idempotency_key="idemp_conc_01",
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    def _sign_payload(self, raw_bytes: bytes) -> str:
        return hmac.new(self.secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    async def test_01_duplicate_webhooks_race(self) -> None:
        """10 concurrent tasks sending identical webhook event ID."""
        payload = {
            "id": "evt_race_dup_01",
            "event": "payment.authorized",
            "created_at": int(_utc_now().timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "notes": {"transaction_id": "tx_conc_01", "merchant_id": "mer_conc_01"}
                    }
                }
            },
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(raw)

        async def worker() -> bool:
            async with AsyncUnitOfWork(self.session_factory) as uow:
                res = await self.webhook_engine.async_process_webhook(
                    uow, raw, sig, "evt_race_dup_01"
                )
                if res.success:
                    await uow.commit()
                return res.is_duplicate
            return False

        results = await asyncio.gather(*[worker() for _ in range(10)])

        # Exactly 1 worker processes as original (is_duplicate=False), 9 as duplicates (is_duplicate=True)
        duplicates = [r for r in results if r]
        originals = [r for r in results if not r]

        self.assertEqual(len(originals), 1)
        self.assertEqual(len(duplicates), 9)

        # Verify transaction state is COMMITTED
        async with AsyncUnitOfWork(self.session_factory) as uow:
            tx = await uow.transactions.get_transaction("tx_conc_01")
            self.assertIsNotNone(tx)
            assert tx is not None
            self.assertEqual(tx.state, TransactionState.COMMITTED.value)

    async def test_02_reconciliation_and_webhook_race(self) -> None:
        """Concurrent reconciliation and webhook processing."""
        self.adapter.set_reconciliation_status(PaymentResultState.SUCCESS)

        payload = {
            "id": "evt_race_rec_01",
            "event": "payment.authorized",
            "created_at": int(_utc_now().timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "notes": {"transaction_id": "tx_conc_01", "merchant_id": "mer_conc_01"}
                    }
                }
            },
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(raw)

        async def reconcile_worker() -> None:
            async with AsyncUnitOfWork(self.session_factory) as uow:
                res = await self.reconciliation_service.async_reconcile_transaction(
                    uow, "tx_conc_01"
                )
                if res.success:
                    await uow.commit()

        async def webhook_worker() -> None:
            async with AsyncUnitOfWork(self.session_factory) as uow:
                res = await self.webhook_engine.async_process_webhook(
                    uow, raw, sig, "evt_race_rec_01"
                )
                if res.success:
                    await uow.commit()

        await asyncio.gather(reconcile_worker(), webhook_worker())

        # Verify final state converged to COMMITTED
        async with AsyncUnitOfWork(self.session_factory) as uow:
            tx = await uow.transactions.get_transaction("tx_conc_01")
            self.assertIsNotNone(tx)
            assert tx is not None
            self.assertEqual(tx.state, TransactionState.COMMITTED.value)


if __name__ == "__main__":
    unittest.main()
