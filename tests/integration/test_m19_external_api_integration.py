"""
M19 External Developer API Integration Acceptance Suite
======================================================
Workstream 9 — Exercises external developer workflows against public API contract.
"""

from __future__ import annotations

import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.factory import create_fastapi_app
from apps.api.domain.identity import hash_credential_secret
import db.session
from db.models.base import Base
from db.models.credential import ApiCredentialModel


class TestM19ExternalAPIIntegration(unittest.TestCase):
    """External API integration acceptance suite."""

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
                key1 = "rzp_live_demo_token_123"
                key2 = "rzp_live_operator_token_123"
                c1 = ApiCredentialModel(
                    credential_id="cred_demo_01",
                    merchant_id="mer_ext_01",
                    credential_prefix="rzp_live_demo",
                    credential_secret_hash=hash_credential_secret(key1),
                    status="ACTIVE",
                    scopes="* operator admin",
                )
                c2 = ApiCredentialModel(
                    credential_id="cred_demo_02",
                    merchant_id="mer_ext_01",
                    credential_prefix="rzp_live_operator",
                    credential_secret_hash=hash_credential_secret(key2),
                    status="ACTIVE",
                    scopes="* operator admin",
                )
                session.add_all([c1, c2])
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

    def test_01_request_id_header_propagation(self) -> None:
        """Verify client-provided X-Request-ID is propagated in response headers."""
        headers = {
            "Authorization": "Bearer rzp_live_demo_token_123",
            "X-Merchant-ID": "mer_ext_01",
            "X-Request-ID": "req_ext_test_99",
        }
        res = self.client.get("/internal/operations/summary", headers=headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Request-ID"), "req_ext_test_99")

    def test_02_idempotent_demo_journey(self) -> None:
        """Verify demo journey endpoint returns standardized execution summary."""
        headers = {
            "Authorization": "Bearer rzp_live_operator_token_123",
            "X-Operator-Token": "rzp_live_operator_token_123",
            "X-Request-ID": "req_demo_01",
        }
        res = self.client.post("/internal/operations/demo/journey", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["state"], "COMMITTED")
        self.assertIn("idempotency_protection", data)
        self.assertEqual(data["idempotency_protection"]["concurrent_requests"], 20)

    def test_03_webhook_subscription_lifecycle(self) -> None:
        """Verify webhook subscription registration, listing, and updating via public endpoints."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "merchant_id": "mer_ext_01",
            "url": "https://api.merchant.com/webhooks",
            "events": ["payment.captured"],
            "secret": "whsec_test_secret_123",
        }
        # 1. Create subscription
        res = self.client.post("/api/webhooks/subscriptions", json=payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        sub_data = res.json()
        self.assertIn("subscription_id", sub_data)
        sub_id = sub_data["subscription_id"]

        # 2. List subscriptions
        res_list = self.client.get("/api/webhooks/subscriptions?merchant_id=mer_ext_01")
        self.assertEqual(res_list.status_code, 200)
        list_data = res_list.json()
        self.assertGreaterEqual(list_data["count"], 1)

        # 3. Update subscription status
        res_up = self.client.patch(
            f"/api/webhooks/subscriptions/{sub_id}",
            json={"status": "DISABLED"},
            headers=headers,
        )
        self.assertEqual(res_up.status_code, 200)
        self.assertEqual(res_up.json()["status"], "DISABLED")


if __name__ == "__main__":
    unittest.main()
