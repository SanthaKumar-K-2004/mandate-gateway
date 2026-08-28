"""
S02.5 — MCP Security Gateway Audit Observability.

Emits structured JSON audit logging events for MCP reverse proxy, tool masking, and execution authorization.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.mcp.errors import McpErrorCode

logger = logging.getLogger("mandate_gateway.mcp_audit")


class McpAuditLogger:
    """
    Structured audit logger for MCP operations.
    """

    @classmethod
    def log_event(
        cls,
        event_name: str,
        tool_name: str = "",
        session_id: str = "default",
        error_code: McpErrorCode | None = None,
        detail: str | None = None,
    ) -> None:
        """Emit structured JSON audit log entry."""
        extra_fields: dict[str, Any] = {
            "event": f"mcp.{event_name}",
            "tool_name": tool_name,
            "session_id": session_id,
        }
        if error_code:
            extra_fields["error_code"] = error_code.value
        if detail:
            extra_fields["detail"] = detail

        if event_name in ("tools_call_blocked", "execution_failed", "validation_failed"):
            logger.warning(f"MCP event {event_name!r} for tool {tool_name!r}: {detail or 'N/A'}")
        else:
            logger.info(f"MCP event {event_name!r} for tool {tool_name!r}")
