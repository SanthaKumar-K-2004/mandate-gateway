"""
S05.3.3 — Mandate Repository.

Domain persistence repository for Buyer Mandates, status lifecycle transitions,
buyer isolation, and database row locking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.mandate_lifecycle import _MANDATE_LEGAL_TRANSITIONS, MandateStateTransitionError
from apps.api.domain.types import MandateStatus
from db.models.budget import BudgetReservationModel
from db.models.mandate import MandateModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class MandateRepository(BaseRepository[MandateModel]):
    """
    Repository for managing Buyer Mandates, status lifecycle transitions, and row locking.

    Transaction Governance:
      - Repository methods flush mutations to the underlying session to trigger database
        constraints (uniqueness, check constraints, foreign keys) without committing.
      - Commit and rollback operations are explicitly controlled by transaction orchestrators.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MandateModel, session)

    async def create_mandate(
        self,
        mandate_id: str,
        buyer_id: str,
        daily_budget_paise: int,
        expires_at: datetime,
        merchant_id: str | None = None,
        category_scope: str | None = None,
        cumulative_budget_paise: int | None = None,
        currency: str = "INR",
        region: str = "IN",
        status: str | MandateStatus = MandateStatus.ACTIVE,
    ) -> MandateModel:
        """Create and persist a new buyer mandate."""
        status_str = status.value if isinstance(status, MandateStatus) else str(status)

        mandate = MandateModel(
            mandate_id=mandate_id,
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            category_scope=category_scope,
            daily_budget_paise=daily_budget_paise,
            cumulative_budget_paise=cumulative_budget_paise,
            currency=currency,
            region=region,
            status=status_str,
            expires_at=expires_at,
        )
        self._session.add(mandate)
        await self._session.flush()
        return mandate

    async def get_mandate(self, mandate_id: str) -> MandateModel | None:
        """Retrieve a mandate by ID."""
        return await self.get_by_id(mandate_id)

    async def get_mandate_for_buyer(self, mandate_id: str, buyer_id: str) -> MandateModel | None:
        """Retrieve a mandate by ID strictly scoped to a specific buyer_id (Buyer Isolation)."""
        stmt = select(MandateModel).where(
            MandateModel.mandate_id == mandate_id,
            MandateModel.buyer_id == buyer_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_mandates_for_buyer(self, buyer_id: str) -> Sequence[MandateModel]:
        """Retrieve all mandates belonging to a specific buyer in deterministic order."""
        stmt = (
            select(MandateModel)
            .where(MandateModel.buyer_id == buyer_id)
            .order_by(MandateModel.created_at.desc(), MandateModel.mandate_id.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_active_mandates_for_buyer(
        self, buyer_id: str, at: datetime | None = None
    ) -> Sequence[MandateModel]:
        """
        Retrieve active, unexpired mandates belonging to a buyer.

        Mandate must have status == 'ACTIVE' and expires_at > check_time.
        """
        check_time = at if at is not None else _utc_now()
        stmt = (
            select(MandateModel)
            .where(
                MandateModel.buyer_id == buyer_id,
                MandateModel.status == MandateStatus.ACTIVE.value,
                MandateModel.expires_at > check_time,
            )
            .order_by(MandateModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def lock_mandate_for_update(self, mandate_id: str) -> MandateModel | None:
        """
        Lock a mandate row using SELECT ... FOR UPDATE.

        Ensures serializable multi-worker execution across concurrent transactions.
        Does not commit the transaction.
        """
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(MandateModel).where(MandateModel.mandate_id == mandate_id)
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def transition_mandate_status(
        self,
        mandate_id: str,
        target_status: str | MandateStatus,
    ) -> MandateModel:
        """
        Perform an explicit lifecycle status transition for a mandate.

        Validates requested transition against _MANDATE_LEGAL_TRANSITIONS.
        Raises MandateStateTransitionError if illegal.
        Flushes session without committing.
        """
        mandate = await self.lock_mandate_for_update(mandate_id)
        if mandate is None:
            raise ValueError(f"Mandate '{mandate_id}' not found.")

        current_enum = MandateStatus(mandate.status)
        target_enum = MandateStatus(target_status) if isinstance(target_status, str) else target_status

        legal_targets = _MANDATE_LEGAL_TRANSITIONS.get(current_enum, frozenset())
        if target_enum not in legal_targets:
            raise MandateStateTransitionError(current_enum, target_enum)

        mandate.status = target_enum.value
        await self._session.flush()
        return mandate

    async def revoke_mandate(self, mandate_id: str) -> MandateModel:
        """Revoke a mandate (transition to REVOKED status)."""
        return await self.transition_mandate_status(mandate_id, MandateStatus.REVOKED)

    async def expire_mandate(self, mandate_id: str) -> MandateModel:
        """Expire a mandate (transition to EXPIRED status)."""
        return await self.transition_mandate_status(mandate_id, MandateStatus.EXPIRED)

    async def get_mandate_reservations(self, mandate_id: str) -> Sequence[BudgetReservationModel]:
        """Fetch all budget reservations associated with a mandate."""
        stmt = (
            select(BudgetReservationModel)
            .where(BudgetReservationModel.mandate_id == mandate_id)
            .order_by(BudgetReservationModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
