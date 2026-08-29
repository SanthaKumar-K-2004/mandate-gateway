"""
Unit tests for S05.3.4 TransactionRepository.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.transaction import TransactionStateError
from apps.api.domain.types import TransactionState
from db.models.transaction import TransactionModel
from db.repository.transaction_repository import TransactionRepository


class TestTransactionRepositoryUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for TransactionRepository."""

    async def test_create_transaction_flushes(self) -> None:
        """Verify create_transaction instantiates entity and flushes."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = TransactionRepository(mock_session)
        tx = await repo.create_transaction(
            transaction_id="tx_unit_1",
            buyer_id="buyer_1",
            merchant_id="m_1",
            mandate_id="man_1",
            amount_paise=5000,
            cart_hash="hash_123",
            idempotency_key="idemp_1",
        )

        self.assertEqual(tx.transaction_id, "tx_unit_1")
        self.assertEqual(tx.amount_paise, 5000)
        self.assertEqual(tx.state, TransactionState.AUTHORIZED.value)
        mock_session.add.assert_called_once_with(tx)
        mock_session.flush.assert_awaited_once()

    async def test_idempotency_mismatch_fails_closed(self) -> None:
        """Verify reusing idempotency key with conflicting context raises ValueError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        existing_tx = TransactionModel(
            transaction_id="tx_orig",
            buyer_id="buyer_1",
            merchant_id="m_1",
            mandate_id="man_1",
            amount_paise=5000,
            cart_hash="hash_123",
            idempotency_key="idemp_reuse",
        )
        mock_result.scalar_one_or_none.return_value = existing_tx
        mock_session.execute.return_value = mock_result

        repo = TransactionRepository(mock_session)
        with self.assertRaises(ValueError) as ctx:
            await repo.create_transaction(
                transaction_id="tx_new",
                buyer_id="buyer_1",
                merchant_id="m_1",
                mandate_id="man_1",
                amount_paise=99999,  # Mismatched amount!
                cart_hash="hash_123",
                idempotency_key="idemp_reuse",
            )
        self.assertIn("mismatch", str(ctx.exception))

    async def test_illegal_state_transition_fails_closed(self) -> None:
        """Verify illegal transition AUTHORIZED -> COMMITTED raises TransactionStateError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        existing_tx = TransactionModel(
            transaction_id="tx_state",
            state=TransactionState.AUTHORIZED.value,
        )
        mock_result.scalar_one_or_none.return_value = existing_tx
        mock_session.execute.return_value = mock_result

        repo = TransactionRepository(mock_session)
        with self.assertRaises(TransactionStateError):
            await repo.transition_transaction_state("tx_state", TransactionState.COMMITTED)

    async def test_provider_unknown_preserves_executing_state(self) -> None:
        """Verify UNKNOWN provider status updates provider_status but leaves state as EXECUTING."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        existing_tx = TransactionModel(
            transaction_id="tx_unk",
            state=TransactionState.EXECUTING.value,
        )
        mock_result.scalar_one_or_none.return_value = existing_tx
        mock_session.execute.return_value = mock_result

        repo = TransactionRepository(mock_session)
        updated = await repo.record_provider_outcome("tx_unk", "UNKNOWN")

        self.assertEqual(updated.provider_status, "UNKNOWN")
        self.assertEqual(updated.state, TransactionState.EXECUTING.value)


if __name__ == "__main__":
    unittest.main()
