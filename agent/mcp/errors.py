"""
S02.5 — MCP Security Gateway Error Codes & Exceptions.

Defines domain exceptions and structured error codes for the MCP reverse proxy and tool masking gateway.
"""

from __future__ import annotations

from enum import Enum


class McpErrorCode(str, Enum):
    """Structured machine-readable error codes for MCP Gateway failures."""

    MCP_TOOL_NOT_FOUND = "MCP_TOOL_NOT_FOUND"
    MCP_TOOL_UNAUTHORIZED = "MCP_TOOL_UNAUTHORIZED"
    MCP_TOOL_BLOCKED = "MCP_TOOL_BLOCKED"
    MCP_INVALID_JSONRPC = "MCP_INVALID_JSONRPC"
    MCP_TRANSACTION_UNAUTHORIZED = "MCP_TRANSACTION_UNAUTHORIZED"
    MCP_EXECUTION_FAILED = "MCP_EXECUTION_FAILED"
    MCP_PAYLOAD_SIZE_EXCEEDED = "MCP_PAYLOAD_SIZE_EXCEEDED"


class McpGatewayError(Exception):
    """Domain error raised during MCP JSON-RPC processing, tool masking, or runtime execution authorization."""

    def __init__(self, code: McpErrorCode, detail: str) -> None:
        super().__init__(f"[{code.value}] {detail}")
        self.code: McpErrorCode = code
        self.detail: str = detail
