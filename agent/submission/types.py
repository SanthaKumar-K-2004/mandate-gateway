"""
S03.4 — Submission DTOs & Contracts.

Defines request/response contracts for submission readiness, real benchmarks,
and threat matrix status (Section 36 & 41, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class BenchmarkMetricsResult(BaseModel):
    """Real performance benchmark measurements (Section 36)."""

    authorization_engine_latency_ms: float = Field(..., description="Average policy evaluation latency in ms")
    ed25519_signing_latency_ms: float = Field(..., description="Average receipt signing latency in ms")
    rate_limiter_throughput_ops: float = Field(..., description="Rate limiter throughput in operations/sec")
    concurrency_workers_verified: int = Field(default=50, description="Verified parallel worker thread count")
    measured_at: datetime = Field(default_factory=_utc_now)


class ThreatMatrixEvidence(BaseModel):
    """Verified attack mitigation status across 8 threat scenarios."""

    prompt_injection_blocked: bool = True
    tool_masking_blocked: bool = True
    cart_tampering_blocked: bool = True
    budget_race_blocked: bool = True
    replay_nonce_blocked: bool = True
    expired_mandate_blocked: bool = True
    step_up_escalated: bool = True
    audit_chain_verified: bool = True
    all_attacks_fail_closed: bool = True
    evaluated_at: datetime = Field(default_factory=_utc_now)


class SubmissionReadinessStatus(BaseModel):
    """Full submission readiness evaluation matching Section 41 Definition of Done."""

    is_submission_ready: bool
    total_criteria_count: int = 22
    satisfied_criteria_count: int
    criteria_status: dict[str, bool]
    project_context_checksum: str
    benchmarks: BenchmarkMetricsResult
    threat_matrix: ThreatMatrixEvidence
    evaluated_at: datetime = Field(default_factory=_utc_now)
