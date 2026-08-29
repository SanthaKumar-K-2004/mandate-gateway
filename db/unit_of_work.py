"""
S05.4.2 — Async Unit of Work & Transaction Manager.

Provides a production-grade asynchronous Unit of Work abstraction that acts
as the SINGLE authorized owner of AsyncSession creation, transaction commit,
rollback, session cleanup, and repository sharing.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from db.repository.audit_repository import AuditRepository
from db.repository.budget_repository import BudgetRepository
from db.repository.mandate_repository import MandateRepository
from db.repository.merchant_repository import MerchantRepository
from db.repository.nonce_repository import NonceRepository
from db.repository.receipt_repository import ReceiptRepository
from db.repository.replay_repository import ReplayRepository
from db.repository.step_up_repository import StepUpRepository
from db.repository.transaction_repository import TransactionRepository

logger = logging.getLogger("mandate_gateway.db.uow")


class UnitOfWorkError(RuntimeError):
    """Base error for Unit of Work failures."""

    pass


class UnitOfWorkClosedError(UnitOfWorkError):
    """Raised when an operation is attempted on a closed Unit of Work."""

    pass


class NestedUnitOfWorkForbiddenError(UnitOfWorkError):
    """Raised when an illegal nested Unit of Work scope is attempted."""

    pass


class AsyncUnitOfWork:
    """
    Asynchronous Unit of Work pattern implementation.

    Guarantees:
      1. Single Session Ownership: Session lifecycle (open, commit, rollback, close)
         is owned exclusively by the UnitOfWork context manager.
      2. Explicit Commit Policy (Option B): Transactions persist ONLY if `await uow.commit()`
         is explicitly called before block exit. Uncommitted context exits fail closed
         and roll back automatically.
      3. Repository Sharing: All repositories accessed via UoW properties share the
         exact same AsyncSession instance.
      4. Exception Propagation: Rollback occurs on error and the original exception
         is re-raised intact.
      5. Nested UoW Prohibition: Nested UoW scopes fail closed.
    """

    def __init__(
        self,
        session_factory: Optional[
            Callable[[], AsyncSession] | async_sessionmaker[AsyncSession]
        ] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        self._session_factory = session_factory
        self._external_session = session
        self._session: Optional[AsyncSession] = None
        self._is_active = False
        self._committed = False
        self._rolled_back = False
        self._closed = False
        self._owns_session = True

        # Cached repository instances bound to active session
        self._merchant_repo: Optional[MerchantRepository] = None
        self._mandate_repo: Optional[MandateRepository] = None
        self._transaction_repo: Optional[TransactionRepository] = None
        self._budget_repo: Optional[BudgetRepository] = None
        self._step_up_repo: Optional[StepUpRepository] = None
        self._replay_repo: Optional[ReplayRepository] = None
        self._nonce_repo: Optional[NonceRepository] = None
        self._audit_repo: Optional[AuditRepository] = None
        self._receipt_repo: Optional[ReceiptRepository] = None

    async def __aenter__(self) -> AsyncUnitOfWork:
        if self._is_active or self._closed:
            raise NestedUnitOfWorkForbiddenError(
                "Nested Unit of Work scopes or re-entering an active/closed UoW is strictly forbidden."
            )

        if self._external_session is not None:
            self._session = self._external_session
            self._owns_session = False
        else:
            if self._session_factory is not None:
                self._session = self._session_factory()
            else:
                from db.session import _async_session_factory

                if _async_session_factory is None:
                    raise UnitOfWorkError(
                        "Database session factory is not initialized. Call initialize_database() first."
                    )
                self._session = _async_session_factory()
            self._owns_session = True

        self._is_active = True
        self._committed = False
        self._rolled_back = False
        self._closed = False
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        try:
            if exc_type is not None:
                # Exception path: rollback transaction and re-raise
                logger.warning(
                    "UnitOfWork exiting due to exception: %s. Rolling back transaction.",
                    exc_val,
                )
                await self.rollback()
            else:
                # Success path: Explicit Commit Policy enforcement
                if not self._committed:
                    logger.info(
                        "UnitOfWork context exited without explicit commit. "
                        "Executing fail-closed rollback to prevent accidental persistence."
                    )
                    await self.rollback()
        finally:
            await self._cleanup()

        # Return False to propagate original exception if present
        return False

    async def commit(self) -> None:
        """
        Explicitly commit the active transaction.

        Must be called by the Application Service before block exit to persist changes.
        """
        self._assert_active()
        if self._committed:
            raise UnitOfWorkError("UnitOfWork has already been committed.")
        if self._rolled_back:
            raise UnitOfWorkError(
                "Cannot commit a transaction that has already been rolled back."
            )

        try:
            assert self._session is not None
            await self._session.flush()
            await self._session.commit()
            self._committed = True
            logger.debug("UnitOfWork transaction committed successfully.")
        except Exception as exc:
            logger.error("UnitOfWork commit failed: %s. Rolling back.", exc)
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """Explicitly roll back the active transaction."""
        if self._closed or self._session is None:
            return
        if not self._rolled_back:
            try:
                await self._session.rollback()
                self._rolled_back = True
                logger.debug("UnitOfWork transaction rolled back.")
            except Exception as exc:
                logger.error("Error during UnitOfWork rollback: %s", exc)

    async def _cleanup(self) -> None:
        """Clean up repository references and close session if owned by UoW."""
        self._is_active = False
        self._closed = True
        self._clear_repo_cache()

        if self._owns_session and self._session is not None:
            try:
                await self._session.close()
            except Exception as exc:
                logger.error("Error closing UnitOfWork AsyncSession: %s", exc)
            finally:
                self._session = None

    def _clear_repo_cache(self) -> None:
        self._merchant_repo = None
        self._mandate_repo = None
        self._transaction_repo = None
        self._budget_repo = None
        self._step_up_repo = None
        self._replay_repo = None
        self._nonce_repo = None
        self._audit_repo = None
        self._receipt_repo = None

    def _assert_active(self) -> None:
        if self._closed or not self._is_active or self._session is None:
            raise UnitOfWorkClosedError(
                "UnitOfWork is closed or inactive and cannot perform operations."
            )

    # -----------------------------------------------------------------------
    # Lazy Repository Access Properties (All Sharing self._session)
    # -----------------------------------------------------------------------

    @property
    def merchants(self) -> MerchantRepository:
        self._assert_active()
        assert self._session is not None
        if self._merchant_repo is None:
            self._merchant_repo = MerchantRepository(self._session)
        return self._merchant_repo

    @property
    def mandates(self) -> MandateRepository:
        self._assert_active()
        assert self._session is not None
        if self._mandate_repo is None:
            self._mandate_repo = MandateRepository(self._session)
        return self._mandate_repo

    @property
    def transactions(self) -> TransactionRepository:
        self._assert_active()
        assert self._session is not None
        if self._transaction_repo is None:
            self._transaction_repo = TransactionRepository(self._session)
        return self._transaction_repo

    @property
    def budgets(self) -> BudgetRepository:
        self._assert_active()
        assert self._session is not None
        if self._budget_repo is None:
            self._budget_repo = BudgetRepository(self._session)
        return self._budget_repo

    @property
    def step_up(self) -> StepUpRepository:
        self._assert_active()
        assert self._session is not None
        if self._step_up_repo is None:
            self._step_up_repo = StepUpRepository(self._session)
        return self._step_up_repo

    @property
    def replay(self) -> ReplayRepository:
        self._assert_active()
        assert self._session is not None
        if self._replay_repo is None:
            self._replay_repo = ReplayRepository(self._session)
        return self._replay_repo

    @property
    def nonces(self) -> NonceRepository:
        self._assert_active()
        assert self._session is not None
        if self._nonce_repo is None:
            self._nonce_repo = NonceRepository(self._session)
        return self._nonce_repo

    @property
    def audit(self) -> AuditRepository:
        self._assert_active()
        assert self._session is not None
        if self._audit_repo is None:
            self._audit_repo = AuditRepository(self._session)
        return self._audit_repo

    @property
    def receipts(self) -> ReceiptRepository:
        self._assert_active()
        assert self._session is not None
        if self._receipt_repo is None:
            self._receipt_repo = ReceiptRepository(self._session)
        return self._receipt_repo
