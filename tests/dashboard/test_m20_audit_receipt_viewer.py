"""
M20 Audit & Action Receipt Viewer Suite
========================================
Workstreams 6 & 7 — Verifies audit ledger hash chain verification endpoint and
Action Receipt signature verification logic.
"""

from __future__ import annotations

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.factory import create_fastapi_app
from apps.api.domain.identity import hash_credential_secret
import db.session
from db.models.base import Base
from db.models.credential import ApiCredentialModel


class TestM20AuditReceiptViewer(unittest.TestCase):
    """Audit & Action Receipt viewer test suite."""

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

    def test_01_verify_audit_chain_endpoint(self) -> None:
        """Verify POST /internal/operations/audit/verify returns audit verification status."""
        headers = {
            "Authorization": "Bearer rzp_live_operator_token_123",
            "X-Operator-Token": "rzp_live_operator_token_123",
        }
        res = self.client.post("/internal/operations/audit/verify", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("is_valid", data)
        self.assertTrue(data["is_valid"])

    def test_02_verify_action_receipt_endpoint(self) -> None:
        """Verify POST /internal/operations/receipts/verify evaluates receipt signatures."""
        headers = {
            "Authorization": "Bearer rzp_live_operator_token_123",
            "X-Operator-Token": "rzp_live_operator_token_123",
        }
        sig_param = "0123456789abcdef" * 4
        res = self.client.post(
            f"/internal/operations/receipts/verify?payload_hash=hash123&signature_hex={sig_param}",
            headers=headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_valid"])


if __name__ == "__main__":
    unittest.main()
