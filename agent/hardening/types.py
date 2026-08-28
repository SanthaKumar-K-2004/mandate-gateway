"""
M04 — Deep System Hardening DTOs and Data Models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class HardeningAuditReport:
    """Forensic report covering M04 whole-system hardening verification."""

    timestamp: datetime = field(default_factory=_utc_now)
    project_context_hash: str = ""
    total_tests_run: int = 0
    all_tests_passed: bool = False
    state_machines_audited: int = 0
    attack_vectors_verified: int = 0
    concurrency_workers_tested: int = 0
    controlled_defects_tested: int = 0
    defects_restored_cleanly: bool = False
    fail_closed_verified: bool = False
    status: str = "COMPLETED"
