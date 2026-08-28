"""
S03.4 — Submission Readiness REST API Router.

Implements REST API endpoints for submission readiness evaluation, performance benchmarks,
and threat matrix status (Section 36 & Section 41, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from typing import Any

from agent.submission.types import (
    BenchmarkMetricsResult,
    SubmissionReadinessStatus,
    ThreatMatrixEvidence,
)
from apps.api.domain.submission import SubmissionReadinessEngine

_SUBMISSION_ENGINE = SubmissionReadinessEngine()


def _get_submission_engine() -> SubmissionReadinessEngine:
    return _SUBMISSION_ENGINE


try:
    from fastapi import APIRouter

    submission_router = APIRouter(prefix="/api/submission", tags=["submission-readiness"])

    @submission_router.get(
        "/readiness",
        response_model=SubmissionReadinessStatus,
        summary="Fetch full submission readiness status matching 22 Definition of Done criteria.",
    )
    def get_submission_readiness_endpoint() -> SubmissionReadinessStatus:
        engine = _get_submission_engine()
        return engine.evaluate_submission_readiness()

    @submission_router.get(
        "/benchmarks",
        response_model=BenchmarkMetricsResult,
        summary="Run and fetch real performance benchmark measurements.",
    )
    def get_benchmarks_endpoint() -> BenchmarkMetricsResult:
        engine = _get_submission_engine()
        return engine.run_performance_benchmarks()

    @submission_router.get(
        "/threat-matrix",
        response_model=ThreatMatrixEvidence,
        summary="Fetch verified threat matrix mitigation status across 8 attack vectors.",
    )
    def get_threat_matrix_endpoint() -> ThreatMatrixEvidence:
        engine = _get_submission_engine()
        return engine.get_threat_matrix_evidence()

except ImportError:  # pragma: no cover
    submission_router: Any = None  # type: ignore[no-redef]
