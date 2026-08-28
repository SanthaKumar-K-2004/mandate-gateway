"""
M04 — Deep System Hardening Agent Interface.

Agent-facing M04HardeningManager exposing audit, concurrency stress,
and threat verification interfaces.
"""

from __future__ import annotations

from typing import Any, Dict

from agent.hardening.types import (
    HardeningAuditReport,
    PenetrationAuditReport,
    RecoveryAuditReport,
    SecurityAuditReport,
)
from apps.api.domain.system_hardening import SystemHardeningEngine


class M04HardeningManager:
    """Agent manager interface for M04 whole-system deep hardening audits."""

    def __init__(self) -> None:
        self.engine = SystemHardeningEngine()

    def run_audit(self) -> HardeningAuditReport:
        """Run full whole-system hardening audit."""
        return self.engine.run_full_system_hardening_audit()

    def run_security_audit(self) -> SecurityAuditReport:
        """Run S04.2 Security & Trust-Boundary Forensic Audit."""
        return self.engine.run_security_trust_boundary_audit()

    def run_recovery_audit(self) -> RecoveryAuditReport:
        """Run S04.4 Crash Consistency, Recovery & Reconciliation Forensic Audit."""
        return self.engine.run_crash_recovery_audit()

    def run_penetration_audit(self) -> PenetrationAuditReport:
        """Run S04.5 Final Whole-System Penetration & Submission-Readiness Forensic Audit."""
        return self.engine.run_full_system_penetration_audit()

    def run_100_worker_stress(self) -> Dict[str, Any]:
        """Run 100-worker thread concurrency stress test."""
        return self.engine.run_100_worker_concurrency_stress()
