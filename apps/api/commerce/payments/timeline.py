"""
S01.12 — Real-Time Payment Event Timeline Manager.

Stores and retrieves authoritative, timestamped execution timeline events for buyer UI
and audit trails.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional

from apps.api.commerce.payments.models import PaymentTimelineEvent


class PaymentTimelineManager:
    """
    Central timeline tracker recording live state transitions for agent transactions.
    """

    def __init__(self) -> None:
        # transaction_id -> list of PaymentTimelineEvent
        self._timelines: Dict[str, List[PaymentTimelineEvent]] = {}

    def record_event(
        self,
        transaction_id: str,
        stage: str,
        label: str,
        detail: str,
        status: str = "COMPLETED",
        is_failed: bool = False,
        metadata: Optional[Dict] = None,
    ) -> PaymentTimelineEvent:
        """Record a timeline event for a transaction."""
        event_id = f"evt_{uuid.uuid4().hex[:10]}"
        evt = PaymentTimelineEvent(
            event_id=event_id,
            timestamp=time.time(),
            stage=stage,
            label=label,
            detail=detail,
            status=status,
            is_failed=is_failed,
            metadata=metadata or {},
        )

        if transaction_id not in self._timelines:
            self._timelines[transaction_id] = []
        self._timelines[transaction_id].append(evt)
        return evt

    def get_timeline(self, transaction_id: str) -> List[PaymentTimelineEvent]:
        """Retrieve all recorded timeline events for a transaction."""
        return self._timelines.get(transaction_id, [])

    def create_default_timeline(
        self, transaction_id: str, prompt: str, amount_paise: int
    ) -> List[PaymentTimelineEvent]:
        """Initialize a complete standard agentic shopping timeline."""
        rupees = amount_paise / 100
        events = [
            ("INTENT_RECEIVED", "Intent Received", f"Parsed shopping prompt: '{prompt}'"),
            (
                "RESEARCH_COMPLETED",
                "Products Researched",
                "Executed live multi-source candidate discovery",
            ),
            (
                "EVIDENCE_VERIFIED",
                "Evidence Verified",
                "Product truth and merchant domain verified",
            ),
            ("CART_OPTIMIZED", "Cart Optimized", f"Optimized candidate total: ₹{rupees:.2f}"),
            (
                "PURCHASE_PLAN_CREATED",
                "Purchase Plan Created",
                f"Plan bound to transaction {transaction_id}",
            ),
        ]
        res = []
        for stage, label, detail in events:
            evt = self.record_event(transaction_id, stage=stage, label=label, detail=detail)
            res.append(evt)
        return res


# Global singleton timeline manager
_timeline_manager = PaymentTimelineManager()


def get_timeline_manager() -> PaymentTimelineManager:
    return _timeline_manager
