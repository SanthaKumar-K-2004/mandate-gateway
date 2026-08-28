"""
S02.5 — MCP Security Gateway Concurrency & Race Condition Tests.
"""

from concurrent.futures import ThreadPoolExecutor
import unittest

from agent.mcp.gateway import McpSecurityGateway
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.types import McpOperation, PolicyDecision


class TestMcpConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = McpSecurityGateway()
        self.allowed_ops = {
            McpOperation.CREATE_ORDER,
            McpOperation.CREATE_PAYMENT_LINK,
            McpOperation.FETCH_PAYMENT,
        }
        self.blocked_ops = {
            McpOperation.PAYOUT,
            McpOperation.SETTLEMENT,
            McpOperation.BANK_TRANSFER,
        }
        self.auth = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
        )

    def test_parallel_mcp_requests(self) -> None:
        """Verify 20 concurrent threads can safely query tools/list and tools/call on McpSecurityGateway."""
        worker_count = 20

        def run_worker(idx: int) -> bool:
            if idx % 2 == 0:
                payload = {"jsonrpc": "2.0", "method": "tools/list", "id": idx}
                res = self.gateway.dispatch(
                    raw_payload=payload,
                    allowed_operations=self.allowed_ops,
                    blocked_operations=self.blocked_ops,
                    session_id=f"sess_{idx}",
                )
                return "result" in res and len(res["result"]["tools"]) == 3
            else:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "create_order", "arguments": {"amount": 500000}},
                    "id": idx,
                }
                res = self.gateway.dispatch(
                    raw_payload=payload,
                    allowed_operations=self.allowed_ops,
                    blocked_operations=self.blocked_ops,
                    gateway_authorization=self.auth,
                    session_id=f"sess_{idx}",
                )
                return "result" in res

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = list(executor.map(run_worker, range(worker_count)))

        self.assertEqual(len(results), worker_count)
        self.assertTrue(all(results))


if __name__ == "__main__":
    unittest.main()
