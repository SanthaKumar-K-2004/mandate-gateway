"""
Mandate Gateway — Commerce Audit Logger (M24)
Append-only structured logging for commerce domain events.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("mandate_gateway.commerce_audit")


class CommerceAuditLogger:
    """Structured audit logger for commerce lifecycle events."""

    @staticmethod
    def log_event(event_name: str, payload: Dict[str, Any]) -> None:
        """Log a structured commerce audit event."""
        logger.info(
            f"Commerce Audit Event '{event_name}'",
            extra={
                "event": event_name,
                "payload": payload,
            },
        )
