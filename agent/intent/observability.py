"""
S02.3 — Intent Audit & Observability Integration.

Emits structured audit log events for AI intent parsing, prompt injection blocking,
catalog poisoning defense, and gateway normalization.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.intent.errors import IntentErrorCode

logger = logging.getLogger("mandate_gateway.intent_audit")


class IntentAuditLogger:
    """
    Structured audit logger for AI Intent Normalization lifecycle events.
    """

    @classmethod
    def log_event(
        cls,
        event_name: str,
        session_id: str = "default",
        error_code: IntentErrorCode | None = None,
        detail: str | None = None,
    ) -> None:
        """Emit structured JSON-compatible audit log entry."""
        extra_fields: dict[str, Any] = {
            "event": f"intent.{event_name}",
            "session_id": session_id,
        }
        if error_code:
            extra_fields["error_code"] = error_code.value
        if detail:
            extra_fields["detail"] = detail

        if event_name in ("rejected", "prompt_injection_blocked", "catalog_poisoning_blocked", "authority_injection_blocked"):
            logger.warning(f"Intent event {event_name!r} for session {session_id!r}: {detail or 'N/A'}")
        else:
            logger.info(f"Intent event {event_name!r} for session {session_id!r}")
