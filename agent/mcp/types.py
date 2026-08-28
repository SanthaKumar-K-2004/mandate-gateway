"""
S02.5 — MCP Data Contracts & Tool Definitions.

Defines MCP JSON-RPC 2.0 messages and tool definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apps.api.domain.types import McpOperation


@dataclass(frozen=True, slots=True)
class McpToolDefinition:
    """
    Metadata definition of an MCP tool.
    """

    name: str
    description: str
    inputSchema: dict[str, Any]
    operation: McpOperation
    is_blocked: bool = False


@dataclass(frozen=True, slots=True)
class McpJsonRpcRequest:
    """
    JSON-RPC 2.0 Request payload.
    """

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: str | int | None = None
    jsonrpc: str = "2.0"


@dataclass(frozen=True, slots=True)
class McpJsonRpcResponse:
    """
    JSON-RPC 2.0 Response payload.
    """

    id: str | int | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert response payload to dictionary."""
        out: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            out["error"] = self.error
        else:
            out["result"] = self.result if self.result is not None else {}
        return out
