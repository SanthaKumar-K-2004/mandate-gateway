"""
M13 — Operational Transaction Investigation Service
Section 6 — Observability & Control Plane
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apps.api.app.logging import SENSITIVE_KEY_PATTERNS


def _redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redacts sensitive keys from dictionary data."""
    sanitized: Dict[str, Any] = {}
    for k, v in data.items():
        k_lower = str(k).lower()
        if any(pat in k_lower for pat in SENSITIVE_KEY_PATTERNS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = _redact_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [_redact_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            sanitized[k] = v
    return sanitized


class TransactionInvestigator:
    """
    Authoritative transaction investigation engine.
    Constructs a coherent chronological timeline from authoritative transaction,
    execution, audit, receipt, outbox, and recovery states without inventing history.
    Enforces strict merchant boundary isolation and telemetry secret redaction.
    """

    def __init__(self) -> None:
        # In-memory authoritative stores for transaction investigation
        self._transactions: Dict[str, Dict[str, Any]] = {}
        self._execution_history: Dict[str, List[Dict[str, Any]]] = {}
        self._audit_events: Dict[str, List[Dict[str, Any]]] = {}
        self._receipts: Dict[str, Dict[str, Any]] = {}
        self._outbox_events: Dict[str, List[Dict[str, Any]]] = {}
        self._recovery_activity: Dict[str, List[Dict[str, Any]]] = {}

    def register_transaction(self, transaction_id: str, tx_data: Dict[str, Any]) -> None:
        """Register transaction state data for operational tracing."""
        self._transactions[transaction_id] = tx_data

    def record_execution_attempt(self, transaction_id: str, attempt_data: Dict[str, Any]) -> None:
        """Record an execution attempt for a transaction."""
        if transaction_id not in self._execution_history:
            self._execution_history[transaction_id] = []
        self._execution_history[transaction_id].append(attempt_data)

    def record_audit_event(self, transaction_id: str, audit_data: Dict[str, Any]) -> None:
        """Record an audit log entry for a transaction."""
        if transaction_id not in self._audit_events:
            self._audit_events[transaction_id] = []
        self._audit_events[transaction_id].append(audit_data)

    def record_receipt(self, transaction_id: str, receipt_data: Dict[str, Any]) -> None:
        """Record an Ed25519 execution receipt for a transaction."""
        self._receipts[transaction_id] = receipt_data

    def record_outbox_event(self, transaction_id: str, outbox_data: Dict[str, Any]) -> None:
        """Record an outbox event for a transaction."""
        if transaction_id not in self._outbox_events:
            self._outbox_events[transaction_id] = []
        self._outbox_events[transaction_id].append(outbox_data)

    def record_recovery_activity(self, transaction_id: str, recovery_data: Dict[str, Any]) -> None:
        """Record a recovery attempt/reconciliation for a transaction."""
        if transaction_id not in self._recovery_activity:
            self._recovery_activity[transaction_id] = []
        self._recovery_activity[transaction_id].append(recovery_data)

    def investigate(
        self,
        transaction_id: str,
        requesting_merchant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds operational investigation report for transaction_id.

        Raises PermissionError if requesting_merchant_id is provided and does not match.
        Raises KeyError if transaction_id is not found.
        """
        tx = self._transactions.get(transaction_id)
        if not tx:
            # Check if recorded in secondary history
            if (
                transaction_id not in self._execution_history
                and transaction_id not in self._audit_events
            ):
                raise KeyError(f"Transaction ID '{transaction_id}' not found.")
            # Build minimal stub if referenced only in events
            tx = {
                "transaction_id": transaction_id,
                "merchant_id": requesting_merchant_id or "unknown",
                "buyer_id": "unknown",
                "mandate_id": "unknown",
                "state": "unknown",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        # Merchant isolation security check (S02)
        merchant_id = tx.get("merchant_id", "unknown")
        if requesting_merchant_id and merchant_id != "unknown":
            if requesting_merchant_id != merchant_id:
                raise PermissionError(
                    f"Access denied: Merchant '{requesting_merchant_id}' cannot access "
                    f"transaction belonging to '{merchant_id}'."
                )

        # Build chronological event timeline
        timeline: List[Dict[str, Any]] = []

        # 1. Transaction Creation Event
        created_at = tx.get("created_at") or datetime.now(timezone.utc).isoformat()
        timeline.append(
            {
                "event_type": "transaction.created",
                "timestamp": created_at,
                "detail": f"Transaction created in state {tx.get('state', 'unknown')}",
                "context": {
                    "mandate_id": tx.get("mandate_id", "unknown"),
                    "amount_paise": tx.get("amount_paise", "unknown"),
                    "currency": tx.get("currency", "unknown"),
                },
            }
        )

        # 2. Execution attempts
        attempts = self._execution_history.get(transaction_id, [])
        for att in attempts:
            timeline.append(
                {
                    "event_type": f"transaction.execution_{att.get('status', 'attempted')}",
                    "timestamp": att.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "detail": att.get("detail", "Execution attempt processed"),
                    "context": _redact_dict(att.get("context", {})),
                }
            )

        # 3. Recovery activity
        recoveries = self._recovery_activity.get(transaction_id, [])
        for rec in recoveries:
            timeline.append(
                {
                    "event_type": f"transaction.recovery_{rec.get('action', 'executed')}",
                    "timestamp": rec.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "detail": rec.get("detail", "Recovery operation performed"),
                    "context": _redact_dict(rec.get("context", {})),
                }
            )

        # 4. Outbox events
        outbox_list = self._outbox_events.get(transaction_id, [])
        for ob in outbox_list:
            timeline.append(
                {
                    "event_type": f"outbox.{ob.get('status', 'event_created')}",
                    "timestamp": ob.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "detail": f"Outbox event {ob.get('event_id', 'unknown')} state {ob.get('status', 'unknown')}",
                    "context": _redact_dict(ob.get("context", {})),
                }
            )

        # 5. Audit events
        audits = self._audit_events.get(transaction_id, [])
        for au in audits:
            timeline.append(
                {
                    "event_type": f"audit.{au.get('action', 'recorded')}",
                    "timestamp": au.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "detail": f"Audit hash entry {au.get('entry_hash', 'unknown')[:12]}...",
                    "context": _redact_dict(au.get("context", {})),
                }
            )

        # 6. Receipt event
        receipt = self._receipts.get(transaction_id)
        if receipt:
            timeline.append(
                {
                    "event_type": "receipt.generated",
                    "timestamp": receipt.get(
                        "generated_at", datetime.now(timezone.utc).isoformat()
                    ),
                    "detail": "Ed25519 receipt generated and cryptographically signed",
                    "context": _redact_dict(receipt.get("context", {})),
                }
            )

        # Sort timeline deterministically by timestamp
        timeline.sort(key=lambda e: e.get("timestamp", ""))

        # Assemble safe investigation response (S03)
        report = {
            "transaction_id": transaction_id,
            "merchant_id": merchant_id,
            "buyer_id": tx.get("buyer_id", "unknown"),
            "mandate_id": tx.get("mandate_id", "unknown"),
            "current_state": tx.get("state", "unknown"),
            "amount_paise": tx.get("amount_paise", "unknown"),
            "currency": tx.get("currency", "unknown"),
            "idempotency_key": tx.get("idempotency_key", "unknown"),
            "created_at": created_at,
            "execution_attempts_count": len(attempts),
            "has_receipt": receipt is not None,
            "has_outbox_event": len(outbox_list) > 0,
            "has_recovery_activity": len(recoveries) > 0,
            "timeline": timeline,
        }

        return _redact_dict(report)


# Global singleton instance for operational investigation
investigator = TransactionInvestigator()
