"""
S02.1 — Tool Boundary & Registry Unit Tests.
"""

from typing import Any
import unittest

from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.registry import ToolRegistry


class DummyCatalogTool(ToolInterface):
    """Dummy catalog search tool for testing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="catalog_search",
            description="Search merchant product catalog",
            input_schema={"query": "str"},
            output_schema={"items": "list"},
            is_trusted=False,
            max_invocations=3,
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        query = arguments.get("query", "")
        return ToolResult(
            tool_name="catalog_search",
            success=True,
            data={"items": [{"name": f"Item matching '{query}'", "price_paise": 5000}]},
        )


class BlockedTool(ToolInterface):
    """Blocked tool for testing."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="direct_payment_tool",
            description="Direct payment attempt (blocked)",
            input_schema={},
            output_schema={},
            is_blocked_by_default=True,
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            tool_name="direct_payment_tool",
            success=False,
            error_message="Should never execute",
        )


class TestToolRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = ToolRegistry()
        self.catalog_tool = DummyCatalogTool()
        self.blocked_tool = BlockedTool()
        self.registry.register_tool(self.catalog_tool)
        self.registry.register_tool(self.blocked_tool)

    def test_registered_tool_execution(self) -> None:
        res = self.registry.execute_tool("catalog_search", {"query": "shoes"})
        self.assertTrue(res.success)
        self.assertEqual(res.tool_name, "catalog_search")
        self.assertIn("items", res.data)

    def test_unregistered_tool_rejection(self) -> None:
        res = self.registry.execute_tool("unknown_tool", {})
        self.assertFalse(res.success)
        self.assertIn("not registered", res.error_message or "")

    def test_blocked_tool_rejection(self) -> None:
        res = self.registry.execute_tool("direct_payment_tool", {})
        self.assertFalse(res.success)
        self.assertIn("blocked by default", res.error_message or "")

    def test_max_invocation_limit_enforcement(self) -> None:
        for _ in range(3):
            res = self.registry.execute_tool("catalog_search", {"query": "test"})
            self.assertTrue(res.success)

        # 4th call must breach max_invocations limit (3)
        res4 = self.registry.execute_tool("catalog_search", {"query": "test"})
        self.assertFalse(res4.success)
        self.assertIn("exceeded maximum allowed invocations", res4.error_message or "")

    def test_prohibited_argument_injection_rejection(self) -> None:
        """Verify code injection and SSRF patterns in tool arguments trigger AgentSecurityViolationError."""
        bad_args = [
            {"query": "__import__('os').system('ls')"},
            {"query": "eval('2+2')"},
            {"query": "exec('import sys')"},
            {"query": "http://localhost:8000/admin"},
            {"query": "file:///etc/passwd"},
        ]
        for arg in bad_args:
            res = self.registry.execute_tool("catalog_search", arg)
            self.assertFalse(res.success)
            self.assertIsNotNone(res.error_code)


if __name__ == "__main__":
    unittest.main()
