"""
Mandate Gateway — Fail-Closed & Graceful Dependency Degradation Matrix
Milestone M13 — Operational Resilience Foundation

Defines explicit system behaviors for handling dependency failures cleanly and predictably.
"""

from __future__ import annotations

import enum
import logging
from typing import Any, Dict

logger = logging.getLogger("mandate_gateway.degradation")


class DependencyState(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class DegradationMode(str, enum.Enum):
    FAIL_CLOSED = "FAIL_CLOSED"
    FAIL_OPEN = "FAIL_OPEN"
    DEGRADED_PERFORMS_RECONCILIATION = "DEGRADED_PERFORMS_RECONCILIATION"
    DURABLE_PENDING = "DURABLE_PENDING"


class DependencyDegradationMatrix:
    """
    Evaluates system operational decisions under dependency degradation.
    Enforces fail-closed rules for core security & financial state while allowing
    safe degradation for non-critical telemetry and outbox delivery.
    """

    def evaluate_postgres_failure(self) -> Dict[str, Any]:
        """
        PostgreSQL failure rule:
        MUST FAIL CLOSED. Unsafe in-memory financial state fallbacks are strictly prohibited.
        Readiness check returns 503.
        """
        logger.critical("PostgreSQL unavailable: Enforcing FAIL_CLOSED state for payments.")
        return {
            "dependency": "postgresql",
            "state": DependencyState.UNAVAILABLE.value,
            "mode": DegradationMode.FAIL_CLOSED.value,
            "readiness_status": 503,
            "action": "Reject new payment operations fail-closed. Do not mutate financial state.",
        }

    def evaluate_redis_failure(self, is_distributed_lock_required: bool = True) -> Dict[str, Any]:
        """
        Redis failure rule:
        If required for distributed lock correctness -> FAIL CLOSED.
        If optional cache -> Degrade safely to fallback local evaluation.
        """
        if is_distributed_lock_required:
            logger.error("Redis unavailable: Distributed lock required. Enforcing FAIL_CLOSED.")
            return {
                "dependency": "redis",
                "state": DependencyState.UNAVAILABLE.value,
                "mode": DegradationMode.FAIL_CLOSED.value,
                "readiness_status": 503,
                "action": "Reject concurrent payment proposals failing distributed lock acquisition.",
            }
        else:
            logger.warning("Redis unavailable: Optional cache role. Degrading safely.")
            return {
                "dependency": "redis",
                "state": DependencyState.DEGRADED.value,
                "mode": "SAFE_CACHE_DEGRADATION",
                "readiness_status": 200,
                "action": "Bypass cache and read directly from primary database.",
            }

    def evaluate_provider_failure(self) -> Dict[str, Any]:
        """
        Provider failure rule:
        Do not duplicate provider calls. Ambiguous outcomes stay in EXECUTING/UNKNOWN state
        until background recovery worker reconciles.
        """
        logger.warning("Payment provider timeout or failure: Marking outcome UNKNOWN for recovery.")
        return {
            "dependency": "razorpay_provider",
            "state": DependencyState.UNAVAILABLE.value,
            "mode": DegradationMode.DEGRADED_PERFORMS_RECONCILIATION.value,
            "readiness_status": 200,
            "action": "Preserve transaction state as EXECUTING/UNKNOWN and schedule background reconciliation.",
        }

    def evaluate_telemetry_failure(self) -> Dict[str, Any]:
        """
        Telemetry exporter failure rule:
        FAIL OPEN for payments. Telemetry failures MUST NEVER interrupt payment execution,
        authorization, or transaction consistency.
        """
        logger.warning(
            "Telemetry exporter failed: Fallback to structured local logging. Payments proceed safely."
        )
        return {
            "dependency": "opentelemetry_exporter",
            "state": DependencyState.UNAVAILABLE.value,
            "mode": DegradationMode.FAIL_OPEN.value,
            "readiness_status": 200,
            "action": "Continue payment execution safely. Log telemetry errors locally.",
        }

    def evaluate_outbox_worker_failure(self) -> Dict[str, Any]:
        """
        Outbox worker failure rule:
        Transactions commit safely to database. Events remain durably pending in outbox table.
        Outbox backlog lag becomes observable via metrics.
        """
        logger.warning("Outbox worker unavailable: Domain events stored durably as PENDING.")
        return {
            "dependency": "outbox_worker",
            "state": DependencyState.UNAVAILABLE.value,
            "mode": DegradationMode.DURABLE_PENDING.value,
            "readiness_status": 200,
            "action": "Commit payment transaction safely. Outbox events remain PENDING until worker recovers.",
        }


# Global singleton degradation matrix
degradation_matrix = DependencyDegradationMatrix()
