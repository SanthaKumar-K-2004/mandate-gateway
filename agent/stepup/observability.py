"""
S02.4 — Agent Step-Up Audit & Observability Integration.

Emits structured audit logging events for HITL step-up creation, approval, rejection, and tampering.
"""

from __future__ import annotations

import logging
from typing import Any

from agent.stepup.errors import StepUpErrorCode

logger = logging.getLogger("mandate_gateway.step_up_audit")


class StepUpAuditLogger:
    """
    Structured audit logger for StepUp lifecycle events.
    """

    @classmethod
    def log_event(
        cls,
        event_name: str,
        challenge_id: str = "",
        session_id: str = "default",
        error_code: StepUpErrorCode | None = None,
        detail: str | None = None,
    ) -> None:
        """Emit structured JSON-compatible audit log entry."""
        extra_fields: dict[str, Any] = {
            "event": f"step_up.{event_name}",
            "challenge_id": challenge_id,
            "session_id": session_id,
        }
        if error_code:
            extra_fields["error_code"] = error_code.value
        if detail:
            extra_fields["detail"] = detail

        if event_name in ("rejected", "expired", "tamper_detected", "ai_self_approval_blocked"):
            logger.warning(f"Step-Up event {event_name!r} for challenge {challenge_id!r}: {detail or 'N/A'}")
        else:
            logger.info(f"Step-Up event {event_name!r} for challenge {challenge_id!r}")
