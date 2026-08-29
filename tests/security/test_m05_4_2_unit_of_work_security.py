"""
Security tests for S05.4.2 AsyncUnitOfWork.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from db.repository.base import BaseRepository
from db.repository.merchant_repository import MerchantRepository
from db.repository.transaction_repository import TransactionRepository
from db.unit_of_work import AsyncUnitOfWork


class MagicMock_SessionMaker:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self) -> AsyncSession:
        return self.session


class TestAsyncUnitOfWorkSecurity(unittest.IsolatedAsyncioTestCase):
    """Security test suite for AsyncUnitOfWork."""

    FORBIDDEN_REPO_TRANSACTION_METHODS = [
        "commit",
        "rollback",
        "begin",
        "execute_raw",
        "update_anything",
        "delete_anything",
    ]

    def test_security_repositories_have_no_transaction_ownership(self) -> None:
        """Verify repositories expose zero transaction lifecycle or escape hatch methods."""
        repos = [BaseRepository, MerchantRepository, TransactionRepository]
        for repo in repos:
            for method_name in self.FORBIDDEN_REPO_TRANSACTION_METHODS:
                self.assertFalse(
                    hasattr(repo, method_name),
                    f"Repository '{repo.__name__}' improperly exposes forbidden method '{method_name}'!",
                )

    async def test_controlled_mutation_a_rollback_bypass_detection(self) -> None:
        """
        Controlled Mutation Proof (Mutation A):
        Verify that exception during UoW execution unconditionally triggers rollback.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        # Trigger exception inside UoW
        with self.assertRaises(ZeroDivisionError):
            async with AsyncUnitOfWork(session_factory=session_factory):
                _ = 1 / 0

        # Rollback MUST have been called
        mock_session.rollback.assert_awaited_once()

    async def test_controlled_mutation_b_accidental_auto_commit_prevention(self) -> None:
        """
        Controlled Mutation Proof (Mutation B):
        Verify that exiting UoW context without calling commit() does NOT call commit() on session.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        async with AsyncUnitOfWork(session_factory=session_factory):
            # No uow.commit() call
            pass

        # Session commit must NEVER be called
        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_awaited_once()

    async def test_controlled_mutation_c_session_fragmentation_prevention(self) -> None:
        """
        Controlled Mutation Proof (Mutation C):
        Verify all repository properties share the exact same AsyncSession reference.
        """
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        async with AsyncUnitOfWork(session_factory=session_factory) as uow:
            s_merchants = uow.merchants.session
            s_mandates = uow.mandates.session
            s_tx = uow.transactions.session
            s_budgets = uow.budgets.session
            s_audit = uow.audit.session

            self.assertIs(s_merchants, mock_session)
            self.assertIs(s_mandates, mock_session)
            self.assertIs(s_tx, mock_session)
            self.assertIs(s_budgets, mock_session)
            self.assertIs(s_audit, mock_session)


if __name__ == "__main__":
    unittest.main()
