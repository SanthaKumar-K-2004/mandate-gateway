"""
S02.5 — Dynamic MCP Tool Masking Engine.

Dynamically filters exposed MCP tools for tools/list to achieve least-privilege attack surface reduction.
"""

from __future__ import annotations

from typing import Dict, List, Set

from agent.mcp.types import McpToolDefinition
from apps.api.domain.types import McpOperation

# Catalog of standard MCP Tools
STANDARD_MCP_TOOLS: List[McpToolDefinition] = [
    McpToolDefinition(
        name="create_order",
        description="Create a Razorpay commerce purchase order.",
        inputSchema={
            "type": "object",
            "properties": {
                "amount": {"type": "integer", "description": "Total amount in paise"},
                "currency": {"type": "string"},
            },
            "required": ["amount", "currency"],
        },
        operation=McpOperation.CREATE_ORDER,
    ),
    McpToolDefinition(
        name="create_payment_link",
        description="Generate a Razorpay payment link for checkout.",
        inputSchema={
            "type": "object",
            "properties": {
                "amount": {"type": "integer"},
                "description": {"type": "string"},
            },
            "required": ["amount"],
        },
        operation=McpOperation.CREATE_PAYMENT_LINK,
    ),
    McpToolDefinition(
        name="fetch_payment",
        description="Fetch status of a payment transaction.",
        inputSchema={
            "type": "object",
            "properties": {
                "payment_id": {"type": "string"},
            },
            "required": ["payment_id"],
        },
        operation=McpOperation.FETCH_PAYMENT,
    ),
    # High-Risk / Admin Tools (Hidden by default for shopping mandates)
    McpToolDefinition(
        name="payout",
        description="Initiate merchant payout to external bank account.",
        inputSchema={
            "type": "object",
            "properties": {"amount": {"type": "integer"}},
        },
        operation=McpOperation.PAYOUT,
        is_blocked=True,
    ),
    McpToolDefinition(
        name="settlement",
        description="Execute immediate balance settlement.",
        inputSchema={"type": "object"},
        operation=McpOperation.SETTLEMENT,
        is_blocked=True,
    ),
    McpToolDefinition(
        name="bank_transfer",
        description="Direct electronic bank transfer.",
        inputSchema={"type": "object"},
        operation=McpOperation.BANK_TRANSFER,
        is_blocked=True,
    ),
]


class McpToolMasker:
    """
    Masking engine for filtering tools/list responses based on session mandate scope.
    """

    def __init__(self, tool_catalog: List[McpToolDefinition] | None = None) -> None:
        self._catalog: List[McpToolDefinition] = tool_catalog or STANDARD_MCP_TOOLS
        self._lookup: Dict[str, McpToolDefinition] = {t.name: t for t in self._catalog}

    def get_tool(self, tool_name: str) -> McpToolDefinition | None:
        """Lookup tool definition by name."""
        return self._lookup.get(tool_name)

    def filter_tools_for_scope(
        self,
        allowed_operations: Set[McpOperation],
        blocked_operations: Set[McpOperation],
    ) -> List[McpToolDefinition]:
        """
        Return filtered tool definitions allowed under current policy scope.

        Least-privilege attack-surface reduction:
        Hidden tools are omitted from the returned list.
        """
        filtered: List[McpToolDefinition] = []
        for tool in self._catalog:
            # 1. Operation must be in allowed_operations
            if tool.operation not in allowed_operations:
                continue
            # 2. Operation must NOT be in blocked_operations
            if tool.operation in blocked_operations:
                continue
            # 3. Tool must not be statically blocked
            if tool.is_blocked:
                continue

            filtered.append(tool)

        return filtered
