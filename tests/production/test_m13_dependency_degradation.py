"""
M13 — Dependency Degradation Matrix Test Suite
Section M13 — Operational Resilience Foundation
"""

import unittest

from apps.api.observability.degradation import (
    DegradationMode,
    DependencyState,
    degradation_matrix,
)


class TestM13DependencyDegradation(unittest.TestCase):
    """Test suite for dependency degradation matrix rules."""

    def test_postgres_unavailable_fails_closed(self) -> None:
        """Verify PostgreSQL failure enforces FAIL_CLOSED state and readiness 503."""
        eval_result = degradation_matrix.evaluate_postgres_failure()
        self.assertEqual(eval_result["dependency"], "postgresql")
        self.assertEqual(eval_result["state"], DependencyState.UNAVAILABLE.value)
        self.assertEqual(eval_result["mode"], DegradationMode.FAIL_CLOSED.value)
        self.assertEqual(eval_result["readiness_status"], 503)

    def test_redis_lock_unavailable_fails_closed(self) -> None:
        """Verify Redis failure for required distributed lock enforces FAIL_CLOSED."""
        eval_result = degradation_matrix.evaluate_redis_failure(is_distributed_lock_required=True)
        self.assertEqual(eval_result["dependency"], "redis")
        self.assertEqual(eval_result["mode"], DegradationMode.FAIL_CLOSED.value)
        self.assertEqual(eval_result["readiness_status"], 503)

    def test_redis_optional_cache_degrades_safely(self) -> None:
        """Verify Redis failure for optional cache degrades safely to direct DB read."""
        eval_result = degradation_matrix.evaluate_redis_failure(is_distributed_lock_required=False)
        self.assertEqual(eval_result["dependency"], "redis")
        self.assertEqual(eval_result["state"], DependencyState.DEGRADED.value)
        self.assertEqual(eval_result["readiness_status"], 200)

    def test_provider_unavailable_triggers_reconciliation(self) -> None:
        """Verify provider failure holds transaction state in EXECUTING/UNKNOWN for recovery scan."""
        eval_result = degradation_matrix.evaluate_provider_failure()
        self.assertEqual(eval_result["dependency"], "razorpay_provider")
        self.assertEqual(
            eval_result["mode"], DegradationMode.DEGRADED_PERFORMS_RECONCILIATION.value
        )
        self.assertEqual(eval_result["readiness_status"], 200)

    def test_telemetry_exporter_failure_fails_open(self) -> None:
        """Verify telemetry exporter failure fails open for payments (payments proceed safely)."""
        eval_result = degradation_matrix.evaluate_telemetry_failure()
        self.assertEqual(eval_result["dependency"], "opentelemetry_exporter")
        self.assertEqual(eval_result["mode"], DegradationMode.FAIL_OPEN.value)
        self.assertEqual(eval_result["readiness_status"], 200)

    def test_outbox_worker_failure_retains_durable_pending_event(self) -> None:
        """Verify outbox worker failure retains events as PENDING in outbox table."""
        eval_result = degradation_matrix.evaluate_outbox_worker_failure()
        self.assertEqual(eval_result["dependency"], "outbox_worker")
        self.assertEqual(eval_result["mode"], DegradationMode.DURABLE_PENDING.value)
        self.assertEqual(eval_result["readiness_status"], 200)


if __name__ == "__main__":
    unittest.main()
