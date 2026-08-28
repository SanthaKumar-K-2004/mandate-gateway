"""
S02.5 — MCP Security Gateway Security & Adversarial Tests.
"""

import unittest

from agent.mcp.gateway import McpSecurityGateway
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.types import McpOperation, PolicyDecision, RejectionReason


class TestMcpSecurity(unittest.TestCase):
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

    def test_hidden_tool_direct_call_blocked(self) -> None:
        """Verify calling hidden/blocked tools directly via tools/call fails closed with error -32001."""
        hidden_tools = ["payout", "settlement", "bank_transfer"]

        for tool_name in hidden_tools:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": {"amount": 500000}},
                "id": 101,
            }

            response = self.gateway.dispatch(
                raw_payload=payload,
                allowed_operations=self.allowed_ops,
                blocked_operations=self.blocked_ops,
            )

            self.assertIn("error", response)
            self.assertEqual(response["error"]["code"], -32001)
            self.assertIn("data", response["error"])
            self.assertIn(
                response["error"]["data"]["error_code"],
                ["MCP_TOOL_BLOCKED", "MCP_TOOL_UNAUTHORIZED"],
            )

    def test_unauthorized_transaction_execution_blocked(self) -> None:
        """Verify calling create_order without pre-authorized Gateway execution approval fails closed."""
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "create_order", "arguments": {"amount": 250000}},
            "id": 102,
        }

        # Case 1: gateway_authorization is None
        resp1 = self.gateway.dispatch(
            raw_payload=payload,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
            gateway_authorization=None,
        )
        self.assertIn("error", resp1)
        self.assertEqual(resp1["error"]["code"], -32001)
        self.assertEqual(resp1["error"]["data"]["error_code"], "MCP_TRANSACTION_UNAUTHORIZED")

        # Case 2: gateway_authorization is REJECTED
        rejected_auth = AuthorizationResult(
            decision=PolicyDecision.REJECT,
            rejection_reason=RejectionReason.AMOUNT_EXCEEDS_MANDATE,
        )
        resp2 = self.gateway.dispatch(
            raw_payload=payload,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
            gateway_authorization=rejected_auth,
        )
        self.assertIn("error", resp2)
        self.assertEqual(resp2["error"]["code"], -32001)
        self.assertEqual(resp2["error"]["data"]["error_code"], "MCP_TRANSACTION_UNAUTHORIZED")

    def test_jsonrpc_malformed_payload_rejected(self) -> None:
        """Verify malformed JSON string payload returns parse error -32700."""
        raw_invalid_json = "{malformed_json: true"
        response = self.gateway.dispatch(
            raw_payload=raw_invalid_json,
            allowed_operations=self.allowed_ops,
            blocked_operations=self.blocked_ops,
        )
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()
