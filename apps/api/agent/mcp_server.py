"""
Mandate Gateway — Razerpay MCP Server Layer
Workstream 5 — Model Context Protocol (MCP) compatible server adapter exposing approved tools.
Enforces strict MCP JSON-RPC protocol schema, permission classification, and tenant binding.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from apps.api.agent.tool_registry import AIToolRegistry, ToolExecutionError

RESTRICTED_MCP_TOOLS = (
    "execute_payment",
    "execute_confirmed_purchase",
    # Direct payment/order execution tools MUST NOT be exposed or callable via autonomous MCP clients
    "create_merchant_order",
)


class RazerpayMCPServer:
    """Model Context Protocol (MCP) adapter layer for Mandate Gateway AI Agent Platform."""

    def __init__(self, tool_registry: Optional[AIToolRegistry] = None) -> None:
        self.tool_registry = tool_registry or AIToolRegistry()

    def handle_mcp_request(
        self, request_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle MCP JSON-RPC protocol request.
        Supports 'tools/list' and 'tools/call' methods.
        Strictly enforces permission boundaries on both tool listing and tool invocation.
        """
        method = request_data.get("method")
        req_id = request_data.get("id", 1)

        if method == "tools/list":
            tools_list = self.tool_registry.list_tools()
            # Filter out direct payment execution tools from autonomous MCP tool discovery
            mcp_tools = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["input_schema"],
                }
                for t in tools_list
                if t["name"] not in RESTRICTED_MCP_TOOLS
            ]
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": mcp_tools},
            }

        elif method == "tools/call":
            params = request_data.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})

            if not name:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": "Missing tool name in params"},
                }

            # Enforce execution barrier: Reject restricted tools even if directly invoked by name
            if name in RESTRICTED_MCP_TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": (
                            f"Security Rejection: Tool '{name}' is restricted and cannot "
                            "be invoked directly via autonomous MCP JSON-RPC protocol."
                        ),
                    },
                }

            try:
                result_data = self.tool_registry.invoke_tool(name, arguments, context=context)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": str(result_data)}],
                        "raw": result_data,
                    },
                }
            except ToolExecutionError as err:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(err)},
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unsupported MCP method: '{method}'"},
            }
