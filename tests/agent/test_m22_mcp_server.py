"""
M22 Razerpay MCP Server Unit Test Suite
========================================
Workstream 5 — Verifies Model Context Protocol (MCP) tool discovery ('tools/list')
and tool execution ('tools/call') adhering to MCP JSON-RPC standards.
"""

from __future__ import annotations

import unittest
from apps.api.agent.mcp_server import RazerpayMCPServer


class TestM22MCPServer(unittest.TestCase):
    """Razerpay MCP server test suite."""

    def setUp(self) -> None:
        self.mcp = RazerpayMCPServer()

    def test_01_mcp_tools_list(self) -> None:
        """Verify MCP tools/list returns list of allowlisted tools excluding execute_payment."""
        req = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        res = self.mcp.handle_mcp_request(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertIn("result", res)
        tools = res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("search_products", tool_names)
        self.assertIn("get_budget_status", tool_names)
        self.assertNotIn("execute_payment", tool_names)

    def test_02_mcp_tools_call_success(self) -> None:
        """Verify MCP tools/call executes allowlisted tool search_products."""
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "search_products", "arguments": {"query": "coffee"}},
            "id": 2,
        }
        res = self.mcp.handle_mcp_request(req)
        self.assertEqual(res["jsonrpc"], "2.0")
        self.assertIn("result", res)
        raw = res["result"]["raw"]
        self.assertGreaterEqual(raw["count"], 1)

    def test_03_mcp_tools_call_unallowlisted_rejected(self) -> None:
        """Verify MCP tools/call rejects unallowlisted tool with error code -32000."""
        req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "unallowlisted_tool", "arguments": {}},
            "id": 3,
        }
        res = self.mcp.handle_mcp_request(req)
        self.assertIn("error", res)
        self.assertEqual(res["error"]["code"], -32000)


if __name__ == "__main__":
    unittest.main()
