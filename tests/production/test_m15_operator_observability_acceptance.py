"""
Production acceptance tests for M15 Internal Operator Observability Endpoints.
"""

import json
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.factory import create_app
from apps.api.observability.forensics import forensic_engine
from apps.api.observability.incident_engine import incident_engine
from db.models.base import Base
import db.session
from db.unit_of_work import AsyncUnitOfWork


class TestM15OperatorObservabilityAcceptance(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.app = create_app(auto_startup=False)
        forensic_engine.clear()
        incident_engine.clear()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        db.session._async_session_factory = self.session_factory

    async def asyncTearDown(self) -> None:
        forensic_engine.clear()
        incident_engine.clear()
        db.session._async_session_factory = None
        await self.engine.dispose()

    async def _make_asgi_request(
        self, path: str, method: str = "GET", headers: list[tuple[bytes, bytes]] | None = None
    ) -> tuple[int, dict[bytes, bytes], bytes]:
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers or [(b"x-operator-token", b"rzp_live_operator_token_123")],
        }
        response_start = {}
        body_parts = []

        async def receive() -> dict:
            return {"type": "http.request"}

        async def send(message: dict) -> None:
            if message["type"] == "http.response.start":
                response_start.update(message)
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        await self.app(scope, receive, send)
        status = response_start.get("status", 500)
        resp_headers = dict(response_start.get("headers", []))
        body = b"".join(body_parts)
        return status, resp_headers, body

    async def test_incidents_endpoint_acceptance(self) -> None:
        """Verify GET /internal/operations/incidents returns registered incidents."""
        incident_engine.raise_incident(
            classification="SECURITY",
            severity="HIGH",
            rule_id="TEST_RULE",
            evidence_summary="Acceptance test incident",
        )

        status, _, body = await self._make_asgi_request("/internal/operations/incidents")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertGreaterEqual(data["count"], 1)

    async def test_security_summary_endpoint_acceptance(self) -> None:
        """Verify GET /internal/operations/security/summary returns security posture report."""
        status, _, body = await self._make_asgi_request("/internal/operations/security/summary")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "SECURE")
        self.assertIn("forensic_events_count", data)

    async def test_reliability_summary_endpoint_acceptance(self) -> None:
        """Verify GET /internal/operations/reliability/summary returns reliability posture report."""
        status, _, body = await self._make_asgi_request("/internal/operations/reliability/summary")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "HEALTHY")

    async def test_transaction_timeline_endpoint_acceptance(self) -> None:
        """Verify GET /internal/operations/transactions/{id}/timeline returns timeline."""
        async with AsyncUnitOfWork() as uow:
            await uow.transactions.create_transaction(
                transaction_id="tx_acc_tl_1",
                buyer_id="buyer_acc_1",
                merchant_id="mer_acc_1",
                mandate_id="man_acc_1",
                amount_paise=5000,
                cart_hash="cart_acc_1",
                idempotency_key="idempotency_acc_1",
            )
            await uow.commit()

        headers = [
            (b"x-operator-token", b"rzp_live_operator_token_123"),
            (b"x-merchant-id", b"mer_acc_1"),
        ]
        status, _, body = await self._make_asgi_request(
            "/internal/operations/transactions/tx_acc_tl_1/timeline", headers=headers
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["transaction_id"], "tx_acc_tl_1")
        self.assertGreaterEqual(data["timeline_length"], 1)


if __name__ == "__main__":
    unittest.main()
