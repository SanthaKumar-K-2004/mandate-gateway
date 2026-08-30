"""
Mandate Gateway — Recovery Objectives & Measurable Timing Tracker
Section M17 — Workstream C: Recovery Objectives
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class RecoverySessionRecord:
    """Measurable disaster recovery session tracking record."""

    session_id: str
    start_time_iso: str
    start_timestamp_s: float
    end_time_iso: Optional[str] = None
    end_timestamp_s: Optional[float] = None
    duration_seconds: float = 0.0
    transactions_reconciled: int = 0
    transactions_left_unknown: int = 0
    outbox_events_recovered: int = 0
    audit_verification_passed: bool = False
    receipt_verification_passed: bool = False
    environment_type: str = "simulated"  # "simulated" or "live_infrastructure"


class RecoveryTracker:
    """
    Tracks, measures, and reports production recovery time objectives (RTO)
    and recovery point objectives (RPO) without fabricating unverified metrics.
    """

    def __init__(self) -> None:
        self._active_sessions: Dict[str, RecoverySessionRecord] = {}

    def start_recovery_session(
        self,
        session_id: str,
        environment_type: str = "simulated",
    ) -> RecoverySessionRecord:
        """Start tracking a disaster recovery session."""
        now = datetime.now(timezone.utc)
        record = RecoverySessionRecord(
            session_id=session_id,
            start_time_iso=now.isoformat(),
            start_timestamp_s=time.time(),
            environment_type=environment_type,
        )
        self._active_sessions[session_id] = record
        return record

    def complete_recovery_session(
        self,
        session_id: str,
        reconciled_count: int,
        unknown_count: int,
        outbox_count: int,
        audit_passed: bool,
        receipt_passed: bool,
    ) -> Dict[str, Any]:
        """Complete tracking a disaster recovery session and compute duration."""
        record = self._active_sessions.get(session_id)
        if record is None:
            raise ValueError(f"Recovery session '{session_id}' not found.")

        now = datetime.now(timezone.utc)
        end_ts = time.time()
        record.end_time_iso = now.isoformat()
        record.end_timestamp_s = end_ts
        record.duration_seconds = max(0.0, end_ts - record.start_timestamp_s)
        record.transactions_reconciled = reconciled_count
        record.transactions_left_unknown = unknown_count
        record.outbox_events_recovered = outbox_count
        record.audit_verification_passed = audit_passed
        record.receipt_verification_passed = receipt_passed

        return {
            "session_id": record.session_id,
            "start_time": record.start_time_iso,
            "end_time": record.end_time_iso,
            "duration_seconds": record.duration_seconds,
            "transactions_reconciled": record.transactions_reconciled,
            "transactions_left_unknown": record.transactions_left_unknown,
            "outbox_events_recovered": record.outbox_events_recovered,
            "audit_verification_passed": record.audit_verification_passed,
            "receipt_verification_passed": record.receipt_verification_passed,
            "environment_type": record.environment_type,
        }


recovery_tracker = RecoveryTracker()
