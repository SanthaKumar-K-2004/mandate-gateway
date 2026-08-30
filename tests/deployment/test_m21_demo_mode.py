"""
M21 Safe Live Demo Mode Test Suite
==================================
Workstream 7 — Verifies demo mode isolation, safe mock provider execution,
zero production provider key mixing, and full domain workflow reuse.
"""

from __future__ import annotations

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.factory import create_fastapi_app
from apps.api.config.settings import Settings
from apps.api.domain.identity import hash_credential_secret
import db.session
from db.models.base import Base
from db.models.credential import ApiCredentialModel


class TestM21DemoMode(unittest.TestCase):
    """Safe live demo mode test suite."""

    def setUp(self) -> None:
        self.app = create_fastapi_app()
        if not self.app:
            self.skipTest("FastAPI not installed")

        import asyncio

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        async def setup_db() -> None:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async_sm = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with async_sm() as session:
                key = "rzp_live_operator_token_123"
                c = ApiCredentialModel(
                    credential_id="cred_op_01",
                    merchant_id="mer_operator",
                    credential_prefix="rzp_live_operator",
                    credential_secret_hash=hash_credential_secret(key),
                    status="ACTIVE",
                    scopes="* operator admin",
                )
                session.add(c)
                await session.commit()

        asyncio.run(setup_db())

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        db.session._async_session_factory = self.session_factory

        from fastapi.testclient import TestClient

        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        import asyncio

        asyncio.run(self.engine.dispose())
        db.session._async_session_factory = None

    def test_01_demo_mode_settings_parsing(self) -> None:
        """Verify DEMO_MODE=true parses correctly into Settings."""
        env = {
            "APP_ENV": "development",
            "DEMO_MODE": "true",
        }
        settings = Settings.from_env(env_dict=env, host_context=True)
        self.assertTrue(settings.demo_mode)

    def test_02_demo_journey_execution(self) -> None:
        """Verify demo journey endpoint executes cleanly through real domain workflow."""
        headers = {
            "Authorization": "Bearer rzp_live_operator_token_123",
            "X-Operator-Token": "rzp_live_operator_token_123",
        }
        res = self.client.post("/internal/operations/demo/journey", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["state"], "COMMITTED")
        self.assertIn("order_Demo", data["provider_reference"])

    def test_03_demo_mode_cannot_leak_production_keys(self) -> None:
        """Verify demo mode settings do not expose production secrets in representation."""
        env = {
            "APP_ENV": "development",
            "DEMO_MODE": "true",
            "POSTGRES_PASSWORD": "my_secret_password_123",
        }
        settings = Settings.from_env(env_dict=env, host_context=True)
        d = settings.to_dict(redact=True)
        self.assertEqual(d["POSTGRES_PASSWORD"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
