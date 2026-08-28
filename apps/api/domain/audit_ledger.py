"""
S02.6 — Cryptographic Audit Ledger Engine.

Implements an append-only, thread-safe, linearizable audit ledger with
hash-chain continuity verification.

Hash chain specification (Section 19, PROJECT_CONTEXT.md):
    H0 = genesis (64 hex zeros: GENESIS_HASH)
    H1 = SHA256(H0 + canonical(payload1))
    H2 = SHA256(H1 + canonical(payload2))
    ...
    Hn = SHA256(Hn-1 + canonical(payloadn))
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Any

from apps.api.domain.audit import GENESIS_HASH, AuditEvent
from apps.api.domain.audit_errors import AuditChainTamperedError
from apps.api.domain.types import AuditEventType


class AuditLedger:
    """
    Thread-safe, append-only cryptographic audit ledger.

    Guarantees:
      - Every event is linked to the previous event's SHA-256 hash.
      - Head hash advances monotonically with each appended event.
      - Complete chain verification detects backwards tampering, deletion, or reordering.
      - Thread safety enforced via internal RLock.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: list[AuditEvent] = []
        self._head_hash: str = GENESIS_HASH

    @property
    def head_hash(self) -> str:
        """Return the current head hash digest of the ledger chain."""
        with self._lock:
            return self._head_hash

    def append_event(
        self,
        event_type: AuditEventType,
        *,
        transaction_id: str | None = None,
        mandate_id: str | None = None,
        merchant_id: str | None = None,
        buyer_id: str | None = None,
        payload: dict[str, Any] | None = None,
        at: datetime | None = None,
    ) -> AuditEvent:
        """
        Append a new AuditEvent to the ledger chain under lock.

        Args:
            event_type: Type of security-relevant event.
            transaction_id: Optional associated transaction ID.
            mandate_id: Optional associated mandate ID.
            merchant_id: Optional associated merchant ID.
            buyer_id: Optional associated buyer ID.
            payload: Structured event data (sanitized, zero secrets).
            at: Optional fixed timestamp for deterministic testing.

        Returns:
            The newly created, immutable, hash-linked AuditEvent.
        """
        with self._lock:
            previous = self._head_hash
            event = AuditEvent.create(
                event_type=event_type,
                previous_hash=previous,
                transaction_id=transaction_id,
                mandate_id=mandate_id,
                merchant_id=merchant_id,
                buyer_id=buyer_id,
                payload=payload,
                at=at,
            )

            # Sanity check event hash integrity
            if not event.verify_hash():
                raise RuntimeError(
                    f"Computed audit event hash for {event_type} failed self-verification."
                )

            self._events.append(event)
            self._head_hash = event.event_hash
            return event

    def verify_chain(self) -> tuple[bool, str | None]:
        """
        Verify complete cryptographic chain integrity from genesis to head.

        Returns:
            (True, None) if the chain is intact and untampered.
            (False, error_message) if any link or hash calculation is corrupted.
        """
        with self._lock:
            if not self._events:
                if self._head_hash != GENESIS_HASH:
                    return False, "Empty ledger head_hash does not match GENESIS_HASH."
                return True, None

            expected_previous = GENESIS_HASH

            for index, event in enumerate(self._events):
                # 1. Verify previous_hash linkage
                if event.previous_hash != expected_previous:
                    return (
                        False,
                        (
                            f"Chain broken at index {index}: event previous_hash "
                            f"'{event.previous_hash}' != expected '{expected_previous}'."
                        ),
                    )

                # 2. Recompute & verify event_hash
                if not event.verify_hash():
                    return (
                        False,
                        (
                            f"Hash calculation invalid at index {index}: "
                            f"event_id '{event.event_id}' payload or headers altered."
                        ),
                    )

                expected_previous = event.event_hash

            # 3. Verify head_hash matches the last event's digest
            if self._head_hash != expected_previous:
                return (
                    False,
                    f"Ledger head_hash '{self._head_hash}' != last event digest '{expected_previous}'.",
                )

            return True, None

    def assert_chain_valid(self) -> None:
        """Raise AuditChainTamperedError if the ledger chain is invalid."""
        is_valid, error_msg = self.verify_chain()
        if not is_valid:
            raise AuditChainTamperedError(
                message=error_msg or "Audit chain integrity verification failed.",
                index=-1,
                expected_hash="",
                actual_hash=self._head_hash,
            )

    def query_events(
        self,
        *,
        transaction_id: str | None = None,
        mandate_id: str | None = None,
        merchant_id: str | None = None,
        buyer_id: str | None = None,
        event_type: AuditEventType | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[AuditEvent]:
        """
        Query recorded audit events matching specified filter criteria.

        Args:
            transaction_id: Filter by transaction ID.
            mandate_id: Filter by mandate ID.
            merchant_id: Filter by merchant ID.
            buyer_id: Filter by buyer ID.
            event_type: Filter by audit event type.
            limit: Maximum number of events to return.
            offset: Skip initial N matching events.

        Returns:
            List of matching AuditEvent objects in chronological order.
        """
        with self._lock:
            results: list[AuditEvent] = []
            skipped = 0

            for event in self._events:
                if transaction_id is not None and event.transaction_id != transaction_id:
                    continue
                if mandate_id is not None and event.mandate_id != mandate_id:
                    continue
                if merchant_id is not None and event.merchant_id != merchant_id:
                    continue
                if buyer_id is not None and event.buyer_id != buyer_id:
                    continue
                if event_type is not None and event.event_type != event_type:
                    continue

                if skipped < offset:
                    skipped += 1
                    continue

                results.append(event)

                if limit is not None and len(results) >= limit:
                    break

            return results

    def get_latest_event_for_transaction(self, transaction_id: str) -> AuditEvent | None:
        """Return the most recent audit event for a transaction ID, or None."""
        with self._lock:
            for event in reversed(self._events):
                if event.transaction_id == transaction_id:
                    return event
            return None

    def count(self) -> int:
        """Return total number of audit events recorded in the ledger."""
        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        """Reset the ledger to empty state with GENESIS_HASH (for test isolation)."""
        with self._lock:
            self._events.clear()
            self._head_hash = GENESIS_HASH
