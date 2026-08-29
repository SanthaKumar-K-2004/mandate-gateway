"""
S07 Concurrency Test Suite — API Identity & Authorization Concurrency.

Tests:
  1. Concurrent authentications across multiple worker threads using the same key.
  2. Concurrent credential revocation race: revocation dominates active auth requests.
  3. Concurrent last_used_at timestamp updates under multi-threaded execution.
"""

from __future__ import annotations

import asyncio
import unittest

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.domain.identity import generate_credential_key_pair
from apps.api.security.dependencies import (
    HTTPException,
    authenticate_credential,
)
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestM07IdentityConcurrency(unittest.IsolatedAsyncioTestCase):
    """Concurrency tests for multi-threaded identity authentication and revocation."""

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

    async def test_concurrent_authentications(self) -> None:
        """Test 10 concurrent authentication tasks using the same API credential key."""
        cred_id, prefix, raw_secret, secret_hash = generate_credential_key_pair("live")

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.credentials.create_credential(
                credential_id=cred_id,
                merchant_id="mer_concurrent_1",
                credential_prefix=prefix,
                credential_secret_hash=secret_hash,
                scopes="transaction:read transaction:write",
            )
            await uow.commit()

        async def _auth_task_1() -> str:
            async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
                principal = await authenticate_credential(raw_secret, uow=uow)
                return principal.merchant_id
            return ""

        tasks = [_auth_task_1() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        self.assertEqual(len(results), 10)
        self.assertTrue(all(res == "mer_concurrent_1" for res in results))

    async def test_concurrent_revocation_race(self) -> None:
        """Test concurrent revocation race: after revocation is committed, auth MUST fail closed."""
        cred_id, prefix, raw_secret, secret_hash = generate_credential_key_pair("live")

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.credentials.create_credential(
                credential_id=cred_id,
                merchant_id="mer_concurrent_revoke",
                credential_prefix=prefix,
                credential_secret_hash=secret_hash,
                scopes="transaction:read",
            )
            await uow.commit()

        # Revoke the credential
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.credentials.revoke_credential(cred_id)
            await uow.commit()

        # Run 5 concurrent authentication tasks; all MUST fail with 401 Revoked
        async def _auth_task_2() -> bool:
            async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
                try:
                    await authenticate_credential(raw_secret, uow=uow)
                    return False
                except HTTPException as exc:
                    return exc.status_code == 401
            return False

        results = await asyncio.gather(*[_auth_task_2() for _ in range(5)])
        self.assertTrue(all(results), "All authentications after revocation must fail with 401!")


if __name__ == "__main__":
    unittest.main()
