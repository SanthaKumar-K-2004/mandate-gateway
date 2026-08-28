"""
S02.5 — Authoritative MCP Runtime Tool Call Authorizer.

Enforces runtime security invariant: hidden tool != authorized tool.
Intercepts tools/call and rejects hidden, unallowed, or unauthorized tools before reaching Razorpay.
"""

from __future__ import annotations

from typing import Set

from agent.mcp.errors import McpErrorCode, McpGatewayError
from agent.mcp.masking import McpToolMasker
from agent.mcp.observability import McpAuditLogger
from apps.api.domain.types import McpOperation


class McpRuntimeAuthorizer:
    """
    Authoritative runtime tools/call authorization engine.
    """

    def __init__(self, masker: McpToolMasker | None = None) -> None:
        self.masker: McpToolMasker = masker or McpToolMasker()

    def authorize_tool_call(
        self,
        tool_name: str,
        allowed_operations: Set[McpOperation],
        blocked_operations: Set[McpOperation],
        gateway_authorized: bool = False,
        session_id: str = "default",
    ) -> None:
        """
        Perform authoritative runtime check for tools/call.

        Core Invariant: hidden tool != authorized tool.
        A malicious agent attempting to call a hidden tool (e.g. payout, settlement)
        is intercepted and rejected here.
        """
        tool = self.masker.get_tool(tool_name)
        if tool is None:
            McpAuditLogger.log_event(
                "tools_call_blocked",
                tool_name=tool_name,
                session_id=session_id,
                error_code=McpErrorCode.MCP_TOOL_NOT_FOUND,
                detail=f"Tool {tool_name!r} is not recognized.",
            )
            raise McpGatewayError(
                McpErrorCode.MCP_TOOL_NOT_FOUND,
                f"MCP tool {tool_name!r} does not exist.",
            )

        # 1. Blocklist check takes precedence
        if tool.is_blocked or tool.operation in blocked_operations:
            McpAuditLogger.log_event(
                "tools_call_blocked",
                tool_name=tool_name,
                session_id=session_id,
                error_code=McpErrorCode.MCP_TOOL_BLOCKED,
                detail=f"Tool {tool_name!r} (operation {tool.operation.value!r}) is explicitly blocked.",
            )
            raise McpGatewayError(
                McpErrorCode.MCP_TOOL_BLOCKED,
                f"MCP tool {tool_name!r} is explicitly blocked by merchant or policy scope.",
            )

        # 2. Allowlist check
        if tool.operation not in allowed_operations:
            McpAuditLogger.log_event(
                "tools_call_blocked",
                tool_name=tool_name,
                session_id=session_id,
                error_code=McpErrorCode.MCP_TOOL_UNAUTHORIZED,
                detail=f"Tool {tool_name!r} is not in allowed operations.",
            )
            raise McpGatewayError(
                McpErrorCode.MCP_TOOL_UNAUTHORIZED,
                f"MCP tool {tool_name!r} is not authorized under current session mandate scope.",
            )

        # 3. Gateway Transaction Authorization check
        if not gateway_authorized:
            McpAuditLogger.log_event(
                "tools_call_blocked",
                tool_name=tool_name,
                session_id=session_id,
                error_code=McpErrorCode.MCP_TRANSACTION_UNAUTHORIZED,
                detail="Transaction lacks pre-authorized Gateway execution approval.",
            )
            raise McpGatewayError(
                McpErrorCode.MCP_TRANSACTION_UNAUTHORIZED,
                f"Execution of MCP tool {tool_name!r} requires Gateway authorization (ALLOW).",
            )

        McpAuditLogger.log_event("tools_call_authorized", tool_name=tool_name, session_id=session_id)
