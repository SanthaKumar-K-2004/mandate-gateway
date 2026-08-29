"""
S05.3.6.1 — StepUpRepository & Durable Human Approval Persistence.

Domain persistence repository for human step-up authorization challenges,
exact-once approval semantics, expiry enforcement, and row locking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.domain.step_up import StepUpChallengeStatus
from db.models.step_up import StepUpChallengeModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class StepUpRepository(BaseRepository[StepUpChallengeModel]):
    """
    Repository for durable management of human step-up approval challenges.

    Core Security Invariant:
      LLM / AI / AGENT ≠ HUMAN STEP-UP APPROVER

    Enforces exact-once approval, terminal state immutability, and expiry checks.

    Transaction Governance:
      - Repository methods flush mutations to the underlying session to trigger database
        constraints without committing.
      - Commit and rollback operations are explicitly controlled by transaction orchestrators.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(StepUpChallengeModel, session)

    async def create_challenge(
        self,
        challenge_id: str,
        transaction_id: str,
        risk_classification: str,
        expires_at: datetime,
        status: str | StepUpChallengeStatus = StepUpChallengeStatus.PENDING,
        approver_metadata: str | None = None,
    ) -> StepUpChallengeModel:
        """Create and persist a new human step-up challenge."""
        status_str = status.value if isinstance(status, StepUpChallengeStatus) else str(status)

        challenge = StepUpChallengeModel(
            challenge_id=challenge_id,
            transaction_id=transaction_id,
            risk_classification=risk_classification,
            expires_at=expires_at,
            status=status_str,
            approver_metadata=approver_metadata,
        )
        self._session.add(challenge)
        await self._session.flush()
        return challenge

    async def get_challenge(self, challenge_id: str) -> StepUpChallengeModel | None:
        """Fetch a challenge by primary key ID."""
        return await self.get_by_id(challenge_id)

    async def get_challenge_for_transaction(
        self, transaction_id: str
    ) -> StepUpChallengeModel | None:
        """Retrieve the latest challenge associated with a transaction."""
        stmt = (
            select(StepUpChallengeModel)
            .where(StepUpChallengeModel.transaction_id == transaction_id)
            .order_by(StepUpChallengeModel.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_challenge_for_update(
        self, challenge_id: str
    ) -> StepUpChallengeModel | None:
        """
        Acquire row lock on StepUpChallengeModel row.

        Issues SELECT ... FOR UPDATE on non-SQLite engines inside caller transaction.
        """
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(StepUpChallengeModel).where(
            StepUpChallengeModel.challenge_id == challenge_id
        )
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def approve_challenge(
        self,
        challenge_id: str,
        approver_id: str,
        metadata: str | None = None,
        at: datetime | None = None,
    ) -> StepUpChallengeModel:
        """
        Atomically approve a human step-up challenge.

        1. Locks challenge row for update.
        2. Validates expiry: if expired, transitions status to EXPIRED and raises ValueError.
        3. Validates status: if not PENDING, raises ValueError (exact-once approval enforcement).
        4. Mutates status to APPROVED, sets approved_at and approver_metadata.
        5. Flushes session without committing.
        """
        check_time = at if at is not None else _utc_now()
        challenge = await self.lock_challenge_for_update(challenge_id)
        if challenge is None:
            raise ValueError(f"Step-up challenge '{challenge_id}' not found.")

        # Expiry security check
        exp_at_utc = (
            challenge.expires_at.replace(tzinfo=timezone.utc)
            if challenge.expires_at.tzinfo is None
            else challenge.expires_at
        )
        if check_time >= exp_at_utc:
            challenge.status = StepUpChallengeStatus.EXPIRED.value
            await self._session.flush()
            raise ValueError(
                f"Cannot approve step-up challenge '{challenge_id}': challenge expired at {challenge.expires_at}."
            )

        # Terminal & exact-once approval state check
        if challenge.status != StepUpChallengeStatus.PENDING.value:
            raise ValueError(
                f"Cannot approve step-up challenge '{challenge_id}': challenge is in state '{challenge.status}', expected 'PENDING'."
            )

        challenge.status = StepUpChallengeStatus.APPROVED.value
        challenge.approved_at = check_time
        challenge.approver_metadata = metadata or f"approved_by:{approver_id}"
        await self._session.flush()
        return challenge

    async def reject_challenge(
        self,
        challenge_id: str,
        reason: str | None = None,
        at: datetime | None = None,
    ) -> StepUpChallengeModel:
        """Atomically reject a pending human step-up challenge."""
        challenge = await self.lock_challenge_for_update(challenge_id)
        if challenge is None:
            raise ValueError(f"Step-up challenge '{challenge_id}' not found.")

        if challenge.status != StepUpChallengeStatus.PENDING.value:
            raise ValueError(
                f"Cannot reject step-up challenge '{challenge_id}': challenge is in state '{challenge.status}', expected 'PENDING'."
            )

        challenge.status = StepUpChallengeStatus.REJECTED.value
        challenge.approver_metadata = reason or "rejected"
        await self._session.flush()
        return challenge

    async def expire_challenge(
        self, challenge_id: str, at: datetime | None = None
    ) -> StepUpChallengeModel:
        """Atomically expire a step-up challenge."""
        challenge = await self.lock_challenge_for_update(challenge_id)
        if challenge is None:
            raise ValueError(f"Step-up challenge '{challenge_id}' not found.")

        if challenge.status == StepUpChallengeStatus.PENDING.value:
            challenge.status = StepUpChallengeStatus.EXPIRED.value
            await self._session.flush()

        return challenge

    async def get_pending_challenges(self) -> Sequence[StepUpChallengeModel]:
        """Fetch all currently pending and unexpired challenges."""
        now = _utc_now()
        stmt = (
            select(StepUpChallengeModel)
            .where(
                StepUpChallengeModel.status == StepUpChallengeStatus.PENDING.value,
                StepUpChallengeModel.expires_at > now,
            )
            .order_by(StepUpChallengeModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
