"""
S05.3.7 — ReceiptRepository & Action Receipt Evidence Persistence.

Domain persistence repository for Ed25519 signed action receipt evidence records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.receipt import ActionReceiptModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ReceiptRepository(BaseRepository[ActionReceiptModel]):
    """
    Repository for durable management of Ed25519 signed Action Receipts.

    Security & Integrity Rules:
      1. Action receipts are immutable cryptographic evidence records.
      2. Repository persists canonical payloads, signatures, and public keys without mutation or re-signing.
      3. Foreign key constraints enforce binding to valid transactions and audit events.
      4. Duplicate creation of existing receipt_id is rejected.
      5. Repository methods flush mutations to underlying session without committing internally.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ActionReceiptModel, session)

    async def create_receipt(
        self,
        receipt_id: str,
        transaction_id: str,
        audit_event_id: str,
        canonical_payload_hash: str,
        signature_hex: str,
        public_key_hex: str,
        created_at: datetime | None = None,
    ) -> ActionReceiptModel:
        """
        Persist a verified, Ed25519-signed action receipt.

        Flushes to session to enforce foreign key and primary key database constraints.
        """
        if not receipt_id or not receipt_id.strip():
            raise ValueError("Receipt ID cannot be empty.")
        if not transaction_id or not transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty.")
        if not audit_event_id or not audit_event_id.strip():
            raise ValueError("Audit Event ID cannot be empty.")
        if not canonical_payload_hash or not canonical_payload_hash.strip():
            raise ValueError("Canonical payload hash cannot be empty.")
        if not signature_hex or not signature_hex.strip():
            raise ValueError("Signature hex cannot be empty.")
        if not public_key_hex or not public_key_hex.strip():
            raise ValueError("Public key hex cannot be empty.")

        rec_time = created_at if created_at is not None else _utc_now()

        receipt = ActionReceiptModel(
            receipt_id=receipt_id.strip(),
            transaction_id=transaction_id.strip(),
            audit_event_id=audit_event_id.strip(),
            canonical_payload_hash=canonical_payload_hash.strip(),
            signature_hex=signature_hex.strip(),
            public_key_hex=public_key_hex.strip(),
            created_at=rec_time,
        )
        self._session.add(receipt)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ValueError(
                f"Failed to create action receipt '{receipt_id}': integrity constraint or foreign key violation."
            ) from exc

        return receipt

    async def get_receipt(self, receipt_id: str) -> ActionReceiptModel | None:
        """Fetch action receipt by primary key receipt_id."""
        if not receipt_id:
            return None
        return await self.get_by_id(receipt_id.strip())

    async def get_receipt_for_transaction(self, transaction_id: str) -> ActionReceiptModel | None:
        """Fetch action receipt bound to a given transaction_id."""
        stmt = select(ActionReceiptModel).where(ActionReceiptModel.transaction_id == transaction_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_receipt_for_audit_event(
        self, audit_event_id: str
    ) -> Sequence[ActionReceiptModel]:
        """Fetch all action receipts linked to an audit event ID."""
        stmt = (
            select(ActionReceiptModel)
            .where(ActionReceiptModel.audit_event_id == audit_event_id)
            .order_by(ActionReceiptModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
