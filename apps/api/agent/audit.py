"""
Mandate Gateway — AI Audit Trail Integration
Workstream 9 — Structured machine-readable AI event audit logger.
Integrates AI agent requests, tool invocations, purchase plans, and confirmation events
into the append-only tamper-evident audit ledger.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from db.unit_of_work import AsyncUnitOfWork


class AIAuditLogger:
    """Audit logger recording AI agent interactions in the append-only audit ledger."""

    @staticmethod
    async def log_agent_event(
        event_type: str,
        request_id: str,
        merchant_id: str,
        buyer_id: str,
        payload: Dict[str, Any],
        uow: Optional[AsyncUnitOfWork] = None,
    ) -> None:
        """Append AI structured event to audit ledger safely."""
        # Sanitize payload: remove raw credential keys
        sanitized = {
            k: v for k, v in payload.items() if "secret" not in k.lower() and "key" not in k.lower()
        }

        if uow is not None and hasattr(uow, "audit"):
            await uow.audit.append_event(
                event_type=event_type,
                transaction_id=request_id,
                merchant_id=merchant_id,
                buyer_id=buyer_id,
                payload=sanitized,
            )
