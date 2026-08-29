"""
S05.3.5 — Budget Repository & Atomic Database Reservations.

Domain persistence repository for durable budget reservations, atomic row-locked daily
budget accounting, and state transition governance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.types import BudgetState
from db.models.budget import BudgetReservationModel
from db.models.mandate import MandateModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class BudgetRepository(BaseRepository[BudgetReservationModel]):
    """
    Repository for managing durable budget reservations and atomic database budget checks.

    Financial Accounting Invariant:
      spent_paise + reserved_paise + requested_paise <= daily_limit_paise

    Transaction Governance:
      - Repository methods flush mutations to the underlying session to trigger database
        constraints (uniqueness, check constraints, foreign keys) without committing.
      - Commit and rollback operations are explicitly controlled by transaction orchestrators.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BudgetReservationModel, session)

    async def create_reservation(
        self,
        reservation_id: str,
        mandate_id: str,
        transaction_id: str,
        requested_paise: int,
        reserved_paise: int,
        state: str | BudgetState = BudgetState.RESERVED,
    ) -> BudgetReservationModel:
        """Persist a new budget reservation."""
        if requested_paise < 0:
            raise ValueError(f"requested_paise cannot be negative, got {requested_paise}.")
        if reserved_paise < 0:
            raise ValueError(f"reserved_paise cannot be negative, got {reserved_paise}.")

        state_str = state.value if isinstance(state, BudgetState) else str(state)

        reservation = BudgetReservationModel(
            reservation_id=reservation_id,
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            requested_paise=requested_paise,
            reserved_paise=reserved_paise,
            state=state_str,
        )
        self._session.add(reservation)
        await self._session.flush()
        return reservation

    async def get_reservation(self, reservation_id: str) -> BudgetReservationModel | None:
        """Fetch a reservation by ID."""
        return await self.get_by_id(reservation_id)

    async def get_reservation_for_transaction(
        self, transaction_id: str
    ) -> BudgetReservationModel | None:
        """Fetch the reservation linked to a transaction."""
        stmt = select(BudgetReservationModel).where(
            BudgetReservationModel.transaction_id == transaction_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reservations_for_mandate(
        self, mandate_id: str
    ) -> Sequence[BudgetReservationModel]:
        """Fetch all reservations for a mandate ordered deterministically."""
        stmt = (
            select(BudgetReservationModel)
            .where(BudgetReservationModel.mandate_id == mandate_id)
            .order_by(
                BudgetReservationModel.created_at.desc(),
                BudgetReservationModel.reservation_id.asc(),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_active_reservations_for_mandate(
        self, mandate_id: str
    ) -> Sequence[BudgetReservationModel]:
        """Fetch active budget-consuming reservations for a mandate."""
        active_states = [
            BudgetState.RESERVED.value,
            BudgetState.COMMITTED.value,
            BudgetState.SPENT.value,
        ]
        stmt = (
            select(BudgetReservationModel)
            .where(
                BudgetReservationModel.mandate_id == mandate_id,
                BudgetReservationModel.state.in_(active_states),
            )
            .order_by(BudgetReservationModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def lock_mandate_budget_for_update(
        self, mandate_id: str
    ) -> MandateModel | None:
        """
        Acquire database row lock on MandateModel row for budget evaluation.

        Issues SELECT ... FOR UPDATE on non-SQLite engines inside caller transaction.
        """
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(MandateModel).where(MandateModel.mandate_id == mandate_id)
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def calculate_reserved_total(self, mandate_id: str) -> int:
        """
        Calculate total paise currently reserved/committed for a mandate.

        Only counts active states (RESERVED, COMMITTED, SPENT).
        Excludes RELEASED and EXPIRED states.
        """
        active_states = [
            BudgetState.RESERVED.value,
            BudgetState.COMMITTED.value,
            BudgetState.SPENT.value,
        ]
        stmt = select(
            func.coalesce(func.sum(BudgetReservationModel.reserved_paise), 0)
        ).where(
            BudgetReservationModel.mandate_id == mandate_id,
            BudgetReservationModel.state.in_(active_states),
        )
        result = await self._session.execute(stmt)
        val = result.scalar()
        return int(val) if val is not None else 0

    async def reserve_budget_atomically(
        self,
        reservation_id: str,
        mandate_id: str,
        transaction_id: str,
        requested_paise: int,
    ) -> BudgetReservationModel:
        """
        Atomically evaluate and reserve mandate budget.

        1. Lock Mandate row for update.
        2. Calculate total currently reserved.
        3. Check available_paise = daily_budget_paise - currently_reserved.
        4. If requested_paise > available_paise or requested_paise <= 0, raise ValueError.
        5. Create and return BudgetReservationModel.
        """
        if requested_paise <= 0:
            raise ValueError(f"requested_paise must be positive, got {requested_paise}.")

        mandate = await self.lock_mandate_budget_for_update(mandate_id)
        if mandate is None:
            raise ValueError(f"Mandate '{mandate_id}' not found.")

        currently_reserved = await self.calculate_reserved_total(mandate_id)
        available_paise = mandate.daily_budget_paise - currently_reserved

        if requested_paise > available_paise:
            raise ValueError(
                f"Budget insufficient: requested {requested_paise} paise, available {available_paise} paise "
                f"(limit={mandate.daily_budget_paise}, active_reserved={currently_reserved})."
            )

        return await self.create_reservation(
            reservation_id=reservation_id,
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            requested_paise=requested_paise,
            reserved_paise=requested_paise,
            state=BudgetState.RESERVED,
        )

    async def commit_reservation(self, reservation_id: str) -> BudgetReservationModel:
        """Commit an active reservation (move to COMMITTED state)."""
        reservation = await self.get_reservation(reservation_id)
        if reservation is None:
            raise ValueError(f"Reservation '{reservation_id}' not found.")

        if reservation.state != BudgetState.RESERVED.value:
            raise ValueError(
                f"Cannot commit reservation '{reservation_id}' in state '{reservation.state}'."
            )

        reservation.state = BudgetState.COMMITTED.value
        reservation.resolved_at = _utc_now()
        await self._session.flush()
        return reservation

    async def release_reservation(self, reservation_id: str) -> BudgetReservationModel:
        """Release an active or expired reservation back to available budget."""
        reservation = await self.get_reservation(reservation_id)
        if reservation is None:
            raise ValueError(f"Reservation '{reservation_id}' not found.")

        if reservation.state == BudgetState.RELEASED.value:
            return reservation

        if reservation.state not in (
            BudgetState.RESERVED.value,
            BudgetState.EXPIRED.value,
        ):
            raise ValueError(
                f"Cannot release reservation '{reservation_id}' in state '{reservation.state}'."
            )

        reservation.state = BudgetState.RELEASED.value
        reservation.resolved_at = _utc_now()
        await self._session.flush()
        return reservation
