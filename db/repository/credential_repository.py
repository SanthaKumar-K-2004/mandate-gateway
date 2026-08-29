"""
S07.2 — API Credential Repository & Persistence Layer.

Domain persistence repository for API credential management, authentication lookup,
revocation, scope storage, and last-used timestamp updates.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.credential import ApiCredentialModel
from db.repository.base import BaseRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class ApiCredentialRepository(BaseRepository[ApiCredentialModel]):
    """
    Repository for durable management of API credentials.

    Invariants:
      1. credential_id is globally unique (Primary Key).
      2. credential_prefix is indexed for fast lookup during authentication.
      3. Repository methods flush mutations without internal commits (UoW owns transaction).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ApiCredentialModel, session)

    async def create_credential(
        self,
        credential_id: str,
        merchant_id: str,
        credential_prefix: str,
        credential_secret_hash: str,
        scopes: str = "",
        expires_at: datetime | None = None,
    ) -> ApiCredentialModel:
        """
        Create and persist a new API credential.

        Args:
            credential_id: Unique identifier for the credential (e.g. 'cred_123').
            merchant_id: Merchant ID owning the credential.
            credential_prefix: Non-secret lookup prefix (e.g. 'rzp_live_abcd').
            credential_secret_hash: Salted SHA-256 hash of the secret.
            scopes: Space-delimited string of granted scopes.
            expires_at: Optional expiration timestamp.
        """
        if not credential_id or not credential_id.strip():
            raise ValueError("credential_id cannot be empty.")
        if not merchant_id or not merchant_id.strip():
            raise ValueError("merchant_id cannot be empty.")
        if not credential_prefix or not credential_prefix.strip():
            raise ValueError("credential_prefix cannot be empty.")
        if not credential_secret_hash or not credential_secret_hash.strip():
            raise ValueError("credential_secret_hash cannot be empty.")

        cred = ApiCredentialModel(
            credential_id=credential_id.strip(),
            merchant_id=merchant_id.strip(),
            credential_prefix=credential_prefix.strip(),
            credential_secret_hash=credential_secret_hash.strip(),
            status="ACTIVE",
            scopes=scopes.strip() if scopes else "",
            created_at=_utc_now(),
            expires_at=expires_at,
        )
        self._session.add(cred)
        await self._session.flush()
        return cred

    async def get_credential(self, credential_id: str) -> ApiCredentialModel | None:
        """Fetch a credential by credential_id."""
        if not credential_id:
            return None
        stmt = select(ApiCredentialModel).where(
            ApiCredentialModel.credential_id == credential_id.strip()
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_credential_by_prefix(self, prefix: str) -> ApiCredentialModel | None:
        """Fetch a credential by its non-secret lookup prefix."""
        if not prefix:
            return None
        stmt = select(ApiCredentialModel).where(
            ApiCredentialModel.credential_prefix == prefix.strip()
        )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_credentials_for_merchant(self, merchant_id: str) -> Sequence[ApiCredentialModel]:
        """Fetch all credentials owned by a specific merchant."""
        if not merchant_id:
            return []
        stmt = select(ApiCredentialModel).where(
            ApiCredentialModel.merchant_id == merchant_id.strip()
        )
        res = await self._session.execute(stmt)
        return res.scalars().all()

    async def revoke_credential(self, credential_id: str) -> ApiCredentialModel | None:
        """
        Revoke an active credential by setting status='REVOKED' and revoked_at.

        Returns:
            Updated ApiCredentialModel if found, else None.
        """
        cred = await self.get_credential(credential_id)
        if cred is None:
            return None

        cred.status = "REVOKED"
        cred.revoked_at = _utc_now()
        await self._session.flush()
        return cred

    async def update_last_used(
        self, credential_id: str, timestamp: datetime | None = None
    ) -> ApiCredentialModel | None:
        """Update last_used_at timestamp for a credential."""
        cred = await self.get_credential(credential_id)
        if cred is None:
            return None

        cred.last_used_at = timestamp or _utc_now()
        await self._session.flush()
        return cred
