"""
S03.4 — Submission Agent Interface.

Agent-facing SubmissionManager exposing readiness status, benchmarks,
and threat matrix reports (Section 36 & Section 41, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from agent.submission.types import (
    BenchmarkMetricsResult,
    SubmissionReadinessStatus,
    ThreatMatrixEvidence,
)
from apps.api.domain.submission import SubmissionReadinessEngine


class SubmissionManager:
    """Agent interface for system submission readiness and benchmark evidence."""

    def __init__(self) -> None:
        self.engine = SubmissionReadinessEngine()

    def get_readiness_status(self) -> SubmissionReadinessStatus:
        """Evaluate system-wide submission readiness against the 22 Definition of Done criteria."""
        return self.engine.evaluate_submission_readiness()

    def get_benchmarks(self) -> BenchmarkMetricsResult:
        """Run and return real performance benchmarks."""
        return self.engine.run_performance_benchmarks()

    def get_threat_matrix(self) -> ThreatMatrixEvidence:
        """Return threat matrix evidence for all 8 security attacks."""
        return self.engine.get_threat_matrix_evidence()
