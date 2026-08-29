"""
Integration tests for S05.3.4 TransactionRepository against SQLite in-memory database.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.transaction import TransactionStateError
from apps.api.domain.types import TransactionState
from db.models.base import Base
from db.repository.mandate_repository import MandateRepository
from db.repository.merchant_repository import MerchantRepository
from db.repository.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestTransactionRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for TransactionRepository using SQLite in-memory engine."""

    async def asyncSetUp(self) -> None:
        """Set up in-memory SQLite database and repository session."""
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.session = self.session_factory()
        self.merchant_repo = MerchantRepository(self.session)
        self.mandate_repo = MandateRepository(self.session)
        self.tx_repo = TransactionRepository(self.session)

        # Seed merchant and mandate
        await self.merchant_repo.create_merchant("m_tx_1", "Tx Merchant")
        exp = _utc_now() + timedelta(days=30)
        await self.mandate_repo.create_mandate(
            mandate_id="man_tx_1",
            buyer_id="buyer_tx_alice",
            merchant_id="m_tx_1",
            daily_budget_paise=1000000,
            expires_at=exp,
        )
        await self.session.commit()

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_transaction_lifecycle_and_idempotency(self) -> None:
        """Verify transaction creation, retrieval, and identical idempotency key replay."""
        tx1 = await self.tx_repo.create_transaction(
            transaction_id="tx_integ_101",
            buyer_id="buyer_tx_alice",
            merchant_id="m_tx_1",
            mandate_id="man_tx_1",
            amount_paise=50000,
            cart_hash="cart_hash_1",
            idempotency_key="idemp_integ_101",
        )
        await self.session.commit()

        self.assertEqual(tx1.transaction_id, "tx_integ_101")

        # Identical replay returns existing transaction
        tx1_replay = await self.tx_repo.create_transaction(
            transaction_id="tx_integ_101",
            buyer_id="buyer_tx_alice",
            merchant_id="m_tx_1",
            mandate_id="man_tx_1",
            amount_paise=50000,
            cart_hash="cart_hash_1",
            idempotency_key="idemp_integ_101",
        )
        self.assertEqual(tx1_replay.transaction_id, "tx_integ_101")

        # Mismatched idempotency key reuse raises ValueError
        with self.assertRaises(ValueError):
            await self.tx_repo.create_transaction(
                transaction_id="tx_integ_mismatch",
                buyer_id="buyer_tx_alice",
                merchant_id="m_tx_1",
                mandate_id="man_tx_1",
                amount_paise=99999,  # Mismatched amount!
                cart_hash="cart_hash_1",
                idempotency_key="idemp_integ_101",
            )

    async def test_buyer_isolation_and_context_binding(self) -> None:
        """Verify get_transaction_for_buyer and get_transaction_for_context isolate access."""
        await self.tx_repo.create_transaction(
            transaction_id="tx_integ_102",
            buyer_id="buyer_tx_alice",
            merchant_id="m_tx_1",
            mandate_id="man_tx_1",
            amount_paise=12000,
            cart_hash="cart_hash_2",
            idempotency_key="idemp_integ_102",
        )
        await self.session.commit()

        # Alice retrieves transaction
        tx_alice = await self.tx_repo.get_transaction_for_buyer("tx_integ_102", "buyer_tx_alice")
        self.assertIsNotNone(tx_alice)

        # Bob accessing Alice's transaction gets None
        tx_bob = await self.tx_repo.get_transaction_for_buyer("tx_integ_102", "buyer_tx_bob")
        self.assertIsNone(tx_bob)

        # Context matching
        tx_ctx = await self.tx_repo.get_transaction_for_context(
            "tx_integ_102", "buyer_tx_alice", "m_tx_1", "man_tx_1"
        )
        self.assertIsNotNone(tx_ctx)

    async def test_state_machine_transitions_and_terminal_lock(self) -> None:
        """Verify legal transitions AUTHORIZED -> EXECUTING -> SUCCESS -> COMMITTED -> COMPLETED -> RECEIPT."""
        await self.tx_repo.create_transaction(
            transaction_id="tx_integ_103",
            buyer_id="buyer_tx_alice",
            merchant_id="m_tx_1",
            mandate_id="man_tx_1",
            amount_paise=25000,
            cart_hash="cart_hash_3",
            idempotency_key="idemp_integ_103",
        )
        await self.session.commit()

        # AUTHORIZED -> EXECUTING
        await self.tx_repo.mark_provider_dispatch_started("tx_integ_103", "pay_rzp_123")
        await self.session.commit()

        # EXECUTING -> SUCCESS
        await self.tx_repo.record_provider_outcome("tx_integ_103", "SUCCESS")
        await self.session.commit()

        # SUCCESS -> COMMITTED -> COMPLETED -> RECEIPT
        await self.tx_repo.transition_transaction_state("tx_integ_103", TransactionState.COMMITTED)
        await self.tx_repo.transition_transaction_state("tx_integ_103", TransactionState.COMPLETED)
        tx_receipt = await self.tx_repo.transition_transaction_state(
            "tx_integ_103", TransactionState.RECEIPT
        )
        self.assertEqual(tx_receipt.state, TransactionState.RECEIPT.value)
        await self.session.commit()

        # RECEIPT is terminal — further transition must fail closed
        with self.assertRaises(TransactionStateError):
            await self.tx_repo.transition_transaction_state(
                "tx_integ_103", TransactionState.EXECUTING
            )

    async def test_provider_unknown_outcome_preservation(self) -> None:
        """Verify UNKNOWN provider status updates status while preserving EXECUTING state for reconciliation."""
        await self.tx_repo.create_transaction(
            transaction_id="tx_integ_104",
            buyer_id="buyer_tx_alice",
            merchant_id="m_tx_1",
            mandate_id="man_tx_1",
            amount_paise=75000,
            cart_hash="cart_hash_4",
            idempotency_key="idemp_integ_104",
        )
        await self.session.commit()

        await self.tx_repo.mark_provider_dispatch_started("tx_integ_104", "pay_rzp_unk")
        await self.session.commit()

        # Record UNKNOWN outcome
        await self.tx_repo.record_provider_outcome("tx_integ_104", "UNKNOWN")
        await self.session.commit()

        tx = await self.tx_repo.get_transaction("tx_integ_104")
        self.assertIsNotNone(tx)
        self.assertEqual(tx.provider_status, "UNKNOWN")  # type: ignore[union-attr]
        self.assertEqual(tx.state, TransactionState.EXECUTING.value)  # type: ignore[union-attr]

        # Must be listed in transactions requiring reconciliation
        reconcile_list = await self.tx_repo.list_transactions_requiring_reconciliation()
        self.assertTrue(any(t.transaction_id == "tx_integ_104" for t in reconcile_list))

    async def test_negative_amount_check_constraint(self) -> None:
        """Verify negative amount_paise raises IntegrityError."""
        with self.assertRaises(IntegrityError):
            await self.tx_repo.create_transaction(
                transaction_id="tx_neg",
                buyer_id="buyer_tx_alice",
                merchant_id="m_tx_1",
                mandate_id="man_tx_1",
                amount_paise=-500,
                cart_hash="cart_hash_neg",
                idempotency_key="idemp_neg",
            )
            await self.session.commit()


if __name__ == "__main__":
    unittest.main()
