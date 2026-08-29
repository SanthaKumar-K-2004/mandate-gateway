"""
Unit tests for S05.4.2 AsyncUnitOfWork.
"""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from db.unit_of_work import (
    AsyncUnitOfWork,
    NestedUnitOfWorkForbiddenError,
    UnitOfWorkClosedError,
)


class TestAsyncUnitOfWorkUnit(unittest.IsolatedAsyncioTestCase):
    """Unit test suite for AsyncUnitOfWork."""

    async def test_session_injection_and_ownership(self) -> None:
        """Verify UoW receives session from factory and manages lifecycle."""
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        uow = AsyncUnitOfWork(session_factory=session_factory)
        async with uow:
            self.assertTrue(uow._is_active)
            self.assertEqual(uow._session, mock_session)

        # After exiting without explicit commit, rollback occurs and session is closed
        mock_session.rollback.assert_awaited()
        mock_session.close.assert_awaited()
        self.assertTrue(uow._closed)

    async def test_repository_sharing_and_caching(self) -> None:
        """Verify all repository properties share exact same session and cache instances."""
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        async with AsyncUnitOfWork(session_factory=session_factory) as uow:
            merchants_1 = uow.merchants
            merchants_2 = uow.merchants
            mandates = uow.mandates
            transactions = uow.transactions
            budgets = uow.budgets
            step_up = uow.step_up
            replay = uow.replay
            nonces = uow.nonces
            audit = uow.audit
            receipts = uow.receipts

            # Instances cached
            self.assertIs(merchants_1, merchants_2)

            # All share same AsyncSession
            self.assertIs(merchants_1.session, mock_session)
            self.assertIs(mandates.session, mock_session)
            self.assertIs(transactions.session, mock_session)
            self.assertIs(budgets.session, mock_session)
            self.assertIs(step_up.session, mock_session)
            self.assertIs(replay.session, mock_session)
            self.assertIs(nonces.session, mock_session)
            self.assertIs(audit.session, mock_session)
            self.assertIs(receipts.session, mock_session)

    async def test_explicit_commit_policy(self) -> None:
        """Verify explicit commit flushes and commits, preventing rollback on exit."""
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        async with AsyncUnitOfWork(session_factory=session_factory) as uow:
            await uow.commit()

        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_exit_without_commit_triggers_rollback(self) -> None:
        """Verify exiting context without commit triggers fail-closed rollback."""
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        async with AsyncUnitOfWork(session_factory=session_factory):
            # Do NOT call uow.commit()
            pass

        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_awaited()

    async def test_exception_in_context_triggers_rollback_and_reraises(self) -> None:
        """Verify exception inside context rolls back transaction and re-raises exception intact."""
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        with self.assertRaises(ValueError) as ctx:
            async with AsyncUnitOfWork(session_factory=session_factory):
                raise ValueError("Domain Business Logic Failure")

        self.assertEqual(str(ctx.exception), "Domain Business Logic Failure")
        mock_session.rollback.assert_awaited()
        mock_session.close.assert_awaited()

    async def test_nested_uow_strictly_forbidden(self) -> None:
        """Verify attempting nested UoW context raises NestedUnitOfWorkForbiddenError."""
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        uow = AsyncUnitOfWork(session_factory=session_factory)
        async with uow:
            with self.assertRaises(NestedUnitOfWorkForbiddenError):
                async with uow:
                    pass

    async def test_operations_on_closed_uow_raise_error(self) -> None:
        """Verify accessing repositories or committing on closed UoW raises UnitOfWorkClosedError."""
        mock_session = AsyncMock(spec=AsyncSession)
        session_factory = MagicMock_SessionMaker(mock_session)

        uow = AsyncUnitOfWork(session_factory=session_factory)
        async with uow:
            await uow.commit()

        with self.assertRaises(UnitOfWorkClosedError):
            _ = uow.merchants

        with self.assertRaises(UnitOfWorkClosedError):
            await uow.commit()


class MagicMock_SessionMaker:
    """Helper mock sessionmaker for tests."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def __call__(self) -> AsyncSession:
        return self.session


if __name__ == "__main__":
    unittest.main()
