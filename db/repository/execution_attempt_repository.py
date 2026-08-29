"""
M07 — ExecutionAttemptRepository & Durable Attempt Ownership Persistence.

Domain persistence repository for managing execution attempt ownership tokens,
provider idempotency key context binding, and payload fingerprint validation.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.execution_attempt import ExecutionAttemptModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def compute_payload_fingerprint(payload: dict[str, Any]) -> str:
    """Compute SHA-256 hex digest of a canonicalized JSON request payload."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ExecutionAttemptRepository(BaseRepository[ExecutionAttemptModel]):
    """
    Repository for managing durable execution attempt ownership.

    Core Invariant:
      Before calling an external provider, an execution attempt must be claimed.
      Reusing an idempotency key with a different merchant or payload fingerprint fails closed.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExecutionAttemptModel, session)

    async def claim_attempt(
        self,
        transaction_id: str,
        merchant_id: str,
        idempotency_key: str,
        payload_fingerprint: str,
        attempt_id: str | None = None,
    ) -> tuple[ExecutionAttemptModel, bool]:
        """
        Atomically claim ownership of an execution attempt.

        Returns:
            (ExecutionAttemptModel, is_existing: bool)
            - If attempt_id or matching idempotency_key exists: validates fingerprint & context,
              returns existing record.
            - If new attempt: creates record in CLAIMED state and flushes session.
        """
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty.")
        if not merchant_id or not merchant_id.strip():
            raise ValueError("Merchant ID cannot be empty.")
        if not idempotency_key or not idempotency_key.strip():
            raise ValueError("Idempotency key cannot be empty.")

        clean_tx = transaction_id.strip()
        clean_mer = merchant_id.strip()
        clean_key = idempotency_key.strip()
        clean_fp = payload_fingerprint.strip()
        att_id = attempt_id or f"attempt_{clean_tx}_{uuid.uuid4().hex[:8]}"

        # 1. Lock existing attempt by idempotency key and merchant
        existing = await self.get_attempt_by_key(clean_mer, clean_key)
        if existing is not None:
            # Context integrity check: transaction_id must match
            if existing.transaction_id != clean_tx:
                raise ValueError(
                    f"Idempotency key context mismatch: key {clean_key!r} bound to transaction "
                    f"'{existing.transaction_id}', attempted for transaction '{clean_tx}'."
                )
            # Payload fingerprint integrity check
            if existing.payload_fingerprint != clean_fp:
                raise ValueError(
                    f"Idempotency key payload tamper detected: key {clean_key!r} bound to fingerprint "
                    f"'{existing.payload_fingerprint[:16]}...', attempted with '{clean_fp[:16]}...'."
                )
            return existing, True

        record = ExecutionAttemptModel(
            attempt_id=att_id,
            transaction_id=clean_tx,
            merchant_id=clean_mer,
            idempotency_key=clean_key,
            payload_fingerprint=clean_fp,
            status="CLAIMED",
            created_at=_utc_now(),
        )
        self._session.add(record)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            dup = await self.get_attempt_by_key(clean_mer, clean_key)
            if dup is not None:
                if dup.transaction_id != clean_tx:
                    raise ValueError(
                        f"Idempotency key context mismatch: key {clean_key!r} bound to transaction "
                        f"'{dup.transaction_id}'."
                    ) from exc
                return dup, True
            raise ValueError(
                f"Execution attempt claim failed due to database constraint: {exc}"
            ) from exc

        return record, False

    async def get_attempt_by_key(
        self, merchant_id: str, idempotency_key: str
    ) -> ExecutionAttemptModel | None:
        """Fetch attempt by merchant ID and idempotency key."""
        stmt = select(ExecutionAttemptModel).where(
            ExecutionAttemptModel.merchant_id == merchant_id.strip(),
            ExecutionAttemptModel.idempotency_key == idempotency_key.strip(),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_attempts_for_transaction(
        self, transaction_id: str
    ) -> Sequence[ExecutionAttemptModel]:
        """Fetch all execution attempts for a transaction ordered by timestamp."""
        stmt = (
            select(ExecutionAttemptModel)
            .where(ExecutionAttemptModel.transaction_id == transaction_id.strip())
            .order_by(ExecutionAttemptModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def lock_attempt_for_update(self, attempt_id: str) -> ExecutionAttemptModel | None:
        """Acquire SELECT ... FOR UPDATE lock on an execution attempt record."""
        bind = getattr(self._session, "bind", None)
        dialect = getattr(bind, "dialect", None)
        dialect_name = getattr(dialect, "name", "") if dialect else ""

        stmt = select(ExecutionAttemptModel).where(
            ExecutionAttemptModel.attempt_id == attempt_id.strip()
        )
        if dialect_name != "sqlite":
            stmt = stmt.with_for_update()

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def record_outcome(
        self,
        attempt_id: str,
        status: str,
        provider_reference: str | None = None,
    ) -> ExecutionAttemptModel:
        """Update and finalize execution attempt outcome."""
        record = await self.lock_attempt_for_update(attempt_id)
        if record is None:
            raise ValueError(f"Execution attempt '{attempt_id}' not found.")

        record.status = status
        if provider_reference:
            record.provider_reference = provider_reference
        record.completed_at = _utc_now()
        await self._session.flush()
        return record
