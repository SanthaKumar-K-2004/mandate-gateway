"""
S02.5 — MCP Security Gateway Unit Tests.
"""

import unittest

from agent.mcp.gateway import McpSecurityGateway
from apps.api.domain.types import McpOperation


class TestMcpGatewayUnit(unittest.TestCase):
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

    def test_tools_list_returns_filtered_tools(self) -> None:
        payload = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        response = self.gateway.dispatch(
            raw_payload=payload,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
        )

        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        tools = response["result"]["tools"]

        tool_names = [t["name"] for t in tools]
        self.assertIn("create_order", tool_names)
        self.assertIn("create_payment_link", tool_names)
        self.assertIn("fetch_payment", tool_names)

        # High-risk / admin tools must be omitted
        self.assertNotIn("payout", tool_names)
        self.assertNotIn("settlement", tool_names)
        self.assertNotIn("bank_transfer", tool_names)

    def test_unknown_method_returns_error_32601(self) -> None:
        payload = {"jsonrpc": "2.0", "method": "tools/unknown", "id": 2}
        response = self.gateway.dispatch(
            raw_payload=payload,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
        )

        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)

    def test_invalid_jsonrpc_version_returns_error_32600(self) -> None:
        payload = {"jsonrpc": "1.0", "method": "tools/list", "id": 3}
        response = self.gateway.dispatch(
            raw_payload=payload,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
        )

        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32600)


if __name__ == "__main__":
    unittest.main()
