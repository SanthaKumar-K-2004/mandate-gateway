"""
S05.3.4 — Transaction Repository.

Domain persistence repository for Transaction state machine lifecycle,
idempotency protection, context binding, provider outcome reconciliation, and row locking.
"""

from __future__ import annotations

from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.transaction import TransactionStateError
from apps.api.domain.types import TransactionState
from db.models.transaction import TransactionModel
from db.repository.base import BaseRepository


class TransactionRepository(BaseRepository[TransactionModel]):
    """
    Repository for managing Transaction lifecycle, idempotency uniqueness, and provider outcomes.

    Transaction Governance:
      - Repository methods flush mutations to the underlying session to trigger database
        constraints (uniqueness, check constraints, foreign keys) without committing.
      - Commit and rollback operations are explicitly controlled by transaction orchestrators.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TransactionModel, session)

    async def create_transaction(
        self,
        transaction_id: str,
        buyer_id: str,
        merchant_id: str,
        mandate_id: str,
        amount_paise: int,
        cart_hash: str,
        idempotency_key: str,
        auth_decision: str = "ALLOW",
        state: str | TransactionState = TransactionState.AUTHORIZED,
        currency: str = "INR",
        region: str = "IN",
        provider_payment_id: str | None = None,
        provider_status: str | None = None,
    ) -> TransactionModel:
        """
        Create and persist a transaction authorization record.

        Enforces idempotency uniqueness: if an existing transaction with the same
        idempotency_key is found:
          - If immutable context matches (buyer_id, merchant_id, mandate_id, amount_paise, cart_hash),
            returns existing transaction.
          - If context mismatches, raises ValueError (Fail Closed).
        """
        state_str = state.value if isinstance(state, TransactionState) else str(state)

        # Check existing idempotency key to prevent mismatch overwrite
        existing = await self.get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            if (
                existing.buyer_id == buyer_id
                and existing.merchant_id == merchant_id
                and existing.mandate_id == mandate_id
                and existing.amount_paise == amount_paise
                and existing.cart_hash == cart_hash
            ):
                return existing
            else:
                raise ValueError(
                    f"Idempotency key '{idempotency_key}' mismatch: attempt to reuse existing key with conflicting context."
                )

        transaction = TransactionModel(
            transaction_id=transaction_id,
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            mandate_id=mandate_id,
            cart_hash=cart_hash,
            amount_paise=amount_paise,
            currency=currency,
            region=region,
            auth_decision=auth_decision,
            state=state_str,
            provider_payment_id=provider_payment_id,
            provider_status=provider_status,
            idempotency_key=idempotency_key,
        )
        self._session.add(transaction)
        await self._session.flush()
        return transaction

    async def get_transaction(self, transaction_id: str) -> TransactionModel | None:
        """Retrieve a transaction by ID."""
        return await self.get_by_id(transaction_id)

    async def get_transaction_for_buyer(
        self, transaction_id: str, buyer_id: str
    ) -> TransactionModel | None:
        """Retrieve a transaction strictly scoped to buyer_id (Buyer Isolation)."""
        stmt = select(TransactionModel).where(
            TransactionModel.transaction_id == transaction_id,
            TransactionModel.buyer_id == buyer_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transaction_for_context(
        self,
        transaction_id: str,
        buyer_id: str,
        merchant_id: str,
        mandate_id: str,
    ) -> TransactionModel | None:
        """Retrieve a transaction verifying strict full authorization context binding."""
        stmt = select(TransactionModel).where(
            TransactionModel.transaction_id == transaction_id,
            TransactionModel.buyer_id == buyer_id,
            TransactionModel.merchant_id == merchant_id,
            TransactionModel.mandate_id == mandate_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transaction_by_idempotency_key(
        self, idempotency_key: str
    ) -> TransactionModel | None:
        """Retrieve a transaction by its unique idempotency key."""
        stmt = select(TransactionModel).where(
            TransactionModel.idempotency_key == idempotency_key
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_transaction_for_update(
        self, transaction_id: str
    ) -> TransactionModel | None:
        """
        Lock a transaction row using SELECT ... FOR UPDATE.

        Ensures serializable execution across concurrent workers without internal commits.
        """
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(TransactionModel).where(
            TransactionModel.transaction_id == transaction_id
        )
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def transition_transaction_state(
        self,
        transaction_id: str,
        target_state: str | TransactionState,
    ) -> TransactionModel:
        """
        Perform a legal transaction state machine transition.

        Validates transition against TransactionState.can_transition_to(target).
        Fails closed on illegal transitions or terminal state mutations.
        Flushes session without committing.
        """
        transaction = await self.lock_transaction_for_update(transaction_id)
        if transaction is None:
            raise ValueError(f"Transaction '{transaction_id}' not found.")

        current_enum = TransactionState(transaction.state)
        target_enum = (
            TransactionState(target_state)
            if isinstance(target_state, str)
            else target_state
        )

        if current_enum.is_terminal():
            raise TransactionStateError(current_enum, target_enum)

        if not current_enum.can_transition_to(target_enum):
            raise TransactionStateError(current_enum, target_enum)

        transaction.state = target_enum.value
        await self._session.flush()
        return transaction

    async def mark_provider_dispatch_started(
        self,
        transaction_id: str,
        provider_payment_id: str | None = None,
    ) -> TransactionModel:
        """Transition transaction state to EXECUTING and record provider dispatch."""
        transaction = await self.transition_transaction_state(
            transaction_id, TransactionState.EXECUTING
        )
        if provider_payment_id is not None:
            transaction.provider_payment_id = provider_payment_id
        transaction.provider_status = "DISPATCHED"
        await self._session.flush()
        return transaction

    async def record_provider_outcome(
        self,
        transaction_id: str,
        provider_status: str,
        provider_payment_id: str | None = None,
    ) -> TransactionModel:
        """
        Record final or transient provider outcome.

        CRITICAL SECURITY RULE:
          An 'UNKNOWN' provider outcome MUST NOT automatically transition the state
          to SUCCESS or FAILURE. If provider_status is 'UNKNOWN', the provider_status field
          is updated, but the transaction state remains unchanged (EXECUTING).
        """
        transaction = await self.lock_transaction_for_update(transaction_id)
        if transaction is None:
            raise ValueError(f"Transaction '{transaction_id}' not found.")

        if provider_payment_id is not None:
            transaction.provider_payment_id = provider_payment_id

        transaction.provider_status = provider_status
        upper_status = provider_status.upper()

        if upper_status in ("SUCCESS", "CAPTURED", "PAID"):
            await self.transition_transaction_state(
                transaction_id, TransactionState.SUCCESS
            )
        elif upper_status in ("FAILURE", "FAILED", "DECLINED"):
            await self.transition_transaction_state(
                transaction_id, TransactionState.FAILURE
            )

        await self._session.flush()
        return transaction

    async def list_transactions_requiring_reconciliation(
        self,
    ) -> Sequence[TransactionModel]:
        """List stale or in-flight transactions requiring reconciliation."""
        stmt = (
            select(TransactionModel)
            .where(
                (TransactionModel.state == TransactionState.EXECUTING.value)
                | (TransactionModel.provider_status == "UNKNOWN")
                | (TransactionModel.provider_status == "DISPATCHED")
            )
            .order_by(TransactionModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
