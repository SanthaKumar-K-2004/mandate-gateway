"""
S02.2 — Tool Audit & Observability Integration.

Emits structured audit logging events for tool lifecycle execution.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.tools.errors import ToolErrorCode

logger = logging.getLogger("mandate_gateway.tool_audit")


class ToolAuditLogger:
    """
    Structured audit logger for ToolRegistry events.
    """

    @classmethod
    def log_event(
        cls,
        event_name: str,
        tool_name: str,
        version: str = "1.0.0",
        session_id: str = "default",
        error_code: ToolErrorCode | None = None,
        detail: str | None = None,
        duration_ms: float = 0.0,
    ) -> None:
        """Emit structured JSON-compatible log entry."""
        extra_fields: dict[str, Any] = {
            "event": f"tool.{event_name}",
            "tool_name": tool_name,
            "tool_version": version,
            "session_id": session_id,
            "duration_ms": duration_ms,
        }
        if error_code:
            extra_fields["error_code"] = error_code.value
        if detail:
            extra_fields["detail"] = detail

        if event_name in ("failed", "validation_failed", "denied", "timed_out"):
            logger.warning(f"Tool event {event_name!r} for {tool_name!r}: {detail or 'N/A'}")
        else:
            logger.info(f"Tool event {event_name!r} for {tool_name!r}")
