"""
M13 Production Operational Acceptance Tests
"""

import json
import unittest
from unittest.mock import AsyncMock, patch

from apps.api.app.factory import create_app
from apps.api.observability.investigation import investigator


class TestM13OperationalAcceptance(unittest.TestCase):
    """Production acceptance tests for M13 operational intelligence & control plane features."""

    def setUp(self) -> None:
        self.app = create_app(auto_startup=False)

    async def _make_asgi_request(
        self, path: str, method: str = "GET", headers: list[tuple[bytes, bytes]] | None = None
    ) -> tuple[int, dict[bytes, bytes], bytes]:
        """Helper to invoke MandateGatewayApp ASGI instance cleanly."""
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

    async def test_liveness_endpoint_production_acceptance(self) -> None:
        """Verify GET /health/live returns HTTP 200 OK."""
        status, headers, body = await self._make_asgi_request("/health/live")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "OK")
        self.assertIn("timestamp", data)
        self.assertIn("service", data)

    async def test_readiness_endpoint_production_acceptance(self) -> None:
        """Verify GET /health/ready returns HTTP 200 OK when instance is READY."""
        status, headers, body = await self._make_asgi_request("/health/ready")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "READY")

    @patch("db.session.check_database_health", new_callable=AsyncMock)
    @patch("db.redis.check_redis_health", new_callable=AsyncMock)
    async def test_dependencies_endpoint_production_acceptance(
        self, mock_redis: AsyncMock, mock_db: AsyncMock
    ) -> None:
        """Verify GET /health/dependencies returns HTTP 200 OK with detailed dependency report."""
        mock_db.return_value = {"status": "CONNECTED"}
        mock_redis.return_value = {"status": "CONNECTED"}

        status, headers, body = await self._make_asgi_request(
            "/health/dependencies", headers=[(b"x-operator-token", b"rzp_live_operator_token_123")]
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("dependencies", data)

    async def test_metrics_endpoint_production_acceptance(self) -> None:
        """Verify GET /metrics returns HTTP 200 text/plain Prometheus metrics."""
        status, headers, body = await self._make_asgi_request(
            "/metrics", headers=[(b"x-operator-token", b"rzp_live_operator_token_123")]
        )
        self.assertEqual(status, 200)
        self.assertTrue(headers.get(b"content-type", b"").startswith(b"text/plain"))
        self.assertIn(b"request_count", body)

    async def test_alerts_endpoint_production_acceptance(self) -> None:
        """Verify GET /internal/operations/alerts returns active alerts summary."""
        status, headers, body = await self._make_asgi_request(
            "/internal/operations/alerts",
            headers=[(b"x-operator-token", b"rzp_live_operator_token_123")],
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("alerts_count", data)

    async def test_transaction_investigation_endpoint_production_acceptance(self) -> None:
        """Verify GET /internal/operations/transactions/{id} returns transaction investigation report."""
        tx_id = "tx_prod_accept_100"
        investigator.register_transaction(
            tx_id,
            {
                "transaction_id": tx_id,
                "merchant_id": "merchant_prod",
                "buyer_id": "buyer_prod",
                "mandate_id": "mandate_prod",
                "state": "COMMITTED",
            },
        )

        headers = [
            (b"x-request-id", b"req_prod_accept_01"),
            (b"x-correlation-id", b"corr_prod_accept_01"),
            (b"x-trace-id", b"trace_prod_accept_01"),
            (b"x-merchant-id", b"merchant_prod"),
            (b"x-operator-token", b"rzp_live_operator_token_123"),
        ]
        status, resp_headers, body = await self._make_asgi_request(
            f"/internal/operations/transactions/{tx_id}", headers=headers
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["transaction_id"], tx_id)
        self.assertEqual(data["merchant_id"], "merchant_prod")


if __name__ == "__main__":
    unittest.main()
