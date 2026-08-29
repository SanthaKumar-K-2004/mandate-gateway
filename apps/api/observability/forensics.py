"""
Section M15 — Forensic Event Engine.

Provides an in-process ring buffer and DB persistence engine for immutable,
cryptographically hashed forensic events across SECURITY, RELIABILITY,
DATA_INTEGRITY, and ABUSE categories.
"""

from __future__ import annotations

import collections
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from apps.api.app.context import get_full_context
from apps.api.app.logging import redact_value
from db.models.forensic_event import ForensicEventModel
from db.unit_of_work import AsyncUnitOfWork

logger = logging.getLogger("mandate_gateway.observability.forensics")


class ForensicEngine:
    """Centralized Forensic Event Recording & Query Engine."""

    def __init__(self, max_ring_buffer_size: int = 1000) -> None:
        self._ring_buffer: collections.deque[ForensicEventModel] = collections.deque(
            maxlen=max_ring_buffer_size
        )

    def _compute_hash_signature(
        self,
        event_id: str,
        event_type: str,
        category: str,
        severity: str,
        correlation_id: str,
        outcome: str,
        payload_str: str,
    ) -> str:
        data = f"{event_id}:{event_type}:{category}:{severity}:{correlation_id}:{outcome}:{payload_str}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    async def record_event(
        self,
        event_type: str,
        category: str,
        severity: str,
        outcome: str,
        target_resource: Optional[str] = None,
        actor_principal_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        uow: Optional[AsyncUnitOfWork] = None,
    ) -> ForensicEventModel:
        """Records a structured forensic event with SHA-256 hash integrity."""
        ctx = get_full_context()
        event_id = f"frn_{uuid.uuid4().hex}"

        corr_id = ctx.get("correlation_id") or ctx.get("request_id") or "corr_anon"
        req_id = ctx.get("request_id")
        trace_id = ctx.get("trace_id")
        effective_merchant_id = merchant_id or ctx.get("merchant_id")

        safe_metadata = redact_value(metadata or {})
        payload_json = json.dumps(safe_metadata, sort_keys=True)

        hash_sig = self._compute_hash_signature(
            event_id=event_id,
            event_type=event_type,
            category=category,
            severity=severity,
            correlation_id=corr_id,
            outcome=outcome,
            payload_str=payload_json,
        )

        model = ForensicEventModel(
            event_id=event_id,
            event_type=event_type,
            category=category,
            severity=severity,
            correlation_id=corr_id,
            request_id=req_id,
            trace_id=trace_id,
            actor_principal_id=actor_principal_id,
            merchant_id=effective_merchant_id,
            target_resource=target_resource,
            outcome=outcome,
            metadata_json=payload_json,
            hash_signature=hash_sig,
        )

        # Store in ring buffer
        self._ring_buffer.append(model)

        # Log structured security/forensic event
        logger.info(
            "Forensic event '%s' [%s/%s] recorded for correlation '%s'",
            event_type,
            category,
            severity,
            corr_id,
            extra={"event_id": event_id, "category": category, "severity": severity},
        )

        # Persist to DB if active unit of work provided
        if uow is not None and uow._is_active:
            await uow.forensics.record_event(model)

        return model

    def query_memory_events(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        merchant_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ForensicEventModel]:
        """Queries in-memory forensic ring buffer."""
        matches: List[ForensicEventModel] = []
        for evt in reversed(self._ring_buffer):
            if category and evt.category != category:
                continue
            if severity and evt.severity != severity:
                continue
            if merchant_id and evt.merchant_id != merchant_id:
                continue
            if correlation_id and evt.correlation_id != correlation_id:
                continue
            matches.append(evt)
            if len(matches) >= limit:
                break
        return matches

    def clear(self) -> None:
        """Clears in-memory ring buffer."""
        self._ring_buffer.clear()


# Global Forensic Engine Instance
forensic_engine = ForensicEngine()
