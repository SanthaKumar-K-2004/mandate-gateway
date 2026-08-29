"""
S07 Integration Tests — API Security & Authorization Integration.

Tests end-to-end credential creation, UoW repository persistence, authentication,
revocation, expiration, scope authorization, and multi-tenant merchant isolation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.domain.identity import generate_credential_key_pair
from apps.api.security.dependencies import (
    HTTPException,
    authenticate_credential,
    verify_merchant_tenant_access,
)
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestApiAuthorizationIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for API authorization and tenant isolation."""

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_credential_persistence_and_authentication(self) -> None:
        """Test durable credential creation in UoW, lookup, and successful authentication."""
        cred_id, prefix, raw_secret, secret_hash = generate_credential_key_pair("live")

        # 1. Create credential in UoW
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.credentials.create_credential(
                credential_id=cred_id,
                merchant_id="mer_tenant_1",
                credential_prefix=prefix,
                credential_secret_hash=secret_hash,
                scopes="transaction:read transaction:write mandate:read",
            )
            await uow.commit()

        # 2. Authenticate using raw_secret
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            principal = await authenticate_credential(raw_secret, uow=uow)

            self.assertEqual(principal.credential_id, cred_id)
            self.assertEqual(principal.merchant_id, "mer_tenant_1")
            self.assertTrue(principal.has_scope("transaction:read"))
            self.assertTrue(principal.has_scope("transaction:write"))
            self.assertFalse(principal.has_scope("admin"))

    async def test_revoked_credential_rejection(self) -> None:
        """Test that revoked credentials fail closed during authentication."""
        cred_id, prefix, raw_secret, secret_hash = generate_credential_key_pair("live")

        # Create and revoke credential
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.credentials.create_credential(
                credential_id=cred_id,
                merchant_id="mer_tenant_2",
                credential_prefix=prefix,
                credential_secret_hash=secret_hash,
                scopes="transaction:read",
            )
            await uow.credentials.revoke_credential(cred_id)
            await uow.commit()

        # Authentication attempt must fail with 401
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            with self.assertRaises(HTTPException) as ctx:
                await authenticate_credential(raw_secret, uow=uow)

            self.assertEqual(ctx.exception.status_code, 401)
            self.assertIn("invalid api authentication credentials", ctx.exception.detail.lower())

    async def test_expired_credential_rejection(self) -> None:
        """Test that expired credentials fail closed during authentication."""
        cred_id, prefix, raw_secret, secret_hash = generate_credential_key_pair("live")
        past_time = datetime.now(tz=timezone.utc) - timedelta(hours=1)

        # Create expired credential
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.credentials.create_credential(
                credential_id=cred_id,
                merchant_id="mer_tenant_3",
                credential_prefix=prefix,
                credential_secret_hash=secret_hash,
                scopes="transaction:read",
                expires_at=past_time,
            )
            await uow.commit()

        # Authentication attempt must fail with 401
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            with self.assertRaises(HTTPException) as ctx:
                await authenticate_credential(raw_secret, uow=uow)

            self.assertEqual(ctx.exception.status_code, 401)
            self.assertIn("invalid api authentication credentials", ctx.exception.detail.lower())

    async def test_tenant_isolation_enforcement(self) -> None:
        """Test multi-tenant isolation rejects cross-merchant access attempts."""
        cred_id, prefix, raw_secret, secret_hash = generate_credential_key_pair("live")

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.credentials.create_credential(
                credential_id=cred_id,
                merchant_id="mer_tenant_alpha",
                credential_prefix=prefix,
                credential_secret_hash=secret_hash,
                scopes="transaction:read",
            )
            await uow.commit()

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            principal = await authenticate_credential(raw_secret, uow=uow)

            # Accessing own merchant passes
            verify_merchant_tenant_access("mer_tenant_alpha", principal)

            # Accessing different merchant raises HTTP 403
            with self.assertRaises(HTTPException) as ctx:
                verify_merchant_tenant_access("mer_tenant_beta", principal)

            self.assertEqual(ctx.exception.status_code, 403)
            self.assertIn("Cross-tenant access denied", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
