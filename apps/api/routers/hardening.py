"""
M04 — Deep System Hardening REST Router.

Exposes REST API endpoints for M04 system audit status and 100-worker concurrency metrics.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from agent.hardening.engine import M04HardeningManager

router = APIRouter(prefix="/api/hardening", tags=["M04 Deep System Hardening"])

_manager = M04HardeningManager()


class HardeningAuditResponse(BaseModel):
    """API response contract for M04 system hardening audit."""

    project_context_hash: str
    total_tests_run: int
    all_tests_passed: bool
    state_machines_audited: int
    attack_vectors_verified: int
    concurrency_workers_tested: int
    status: str


@router.get("/audit", response_model=HardeningAuditResponse)
def get_hardening_audit() -> Dict[str, Any]:
    """Return whole-system hardening audit report."""
    try:
        rep = _manager.run_audit()
        return {
            "project_context_hash": rep.project_context_hash,
            "total_tests_run": rep.total_tests_run,
            "all_tests_passed": rep.all_tests_passed,
            "state_machines_audited": rep.state_machines_audited,
            "attack_vectors_verified": rep.attack_vectors_verified,
            "concurrency_workers_tested": rep.concurrency_workers_tested,
            "status": rep.status,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hardening audit failed: {exc}",
        )


@router.get("/concurrency-stress")
def get_concurrency_stress_report() -> Dict[str, Any]:
    """Run and return 100-worker concurrency stress metrics."""
    try:
        return _manager.run_100_worker_stress()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Concurrency stress test failed: {exc}",
        )
