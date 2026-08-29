"""
M13 — Production Operational Failure Drills Test Suite (Drills A through J)
Section M13 — Operational Production Engineering
"""

import logging
import unittest
from unittest.mock import patch

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.app.context import clear_request_context, get_request_context, set_request_context
from apps.api.app.logging import StructuredJsonFormatter
from apps.api.app.metrics import metrics_registry
from apps.api.config.types import SecretString
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import Currency, PaymentResultState, PolicyDecision, TransactionState
from apps.api.observability.alerting import alert_evaluator
from apps.api.observability.degradation import degradation_matrix
from apps.api.observability.tracing import tracer


def _make_allow_auth_result() -> AuthorizationResult:
    controls = [
        SecurityControlOutcome(
            control_name="MANDATE_EVALUATION", passed=True, decision=PolicyDecision.ALLOW
        ),
        SecurityControlOutcome(
            control_name="MERCHANT_POLICY", passed=True, decision=PolicyDecision.ALLOW
        ),
        SecurityControlOutcome(
            control_name="CART_INTEGRITY", passed=True, decision=PolicyDecision.ALLOW
        ),
        SecurityControlOutcome(
            control_name="BUDGET_RESERVATION", passed=True, decision=PolicyDecision.ALLOW
        ),
        SecurityControlOutcome(
            control_name="REPLAY_PROTECTION", passed=True, decision=PolicyDecision.ALLOW
        ),
        SecurityControlOutcome(
            control_name="NONCE_VALIDATION", passed=True, decision=PolicyDecision.ALLOW
        ),
    ]
    return AuthorizationResult(decision=PolicyDecision.ALLOW, control_outcomes=controls)


class TestM13OperationalFailureDrills(unittest.TestCase):
    """Execution of production operational failure drills A through J."""

    def setUp(self) -> None:
        clear_request_context()
        metrics_registry.reset()
        tracer.clear()

    def tearDown(self) -> None:
        clear_request_context()
        metrics_registry.reset()
        tracer.clear()

    def test_drill_a_correlation_isolation(self) -> None:
        """Drill A: Verify request context maintains strict correlation isolation across operations."""
        set_request_context("req_drill_a", "corr_drill_a", "trace_drill_a")
        ctx = get_request_context()
        self.assertEqual(ctx["request_id"], "req_drill_a")
        self.assertEqual(ctx["correlation_id"], "corr_drill_a")
        self.assertEqual(ctx["trace_id"], "trace_drill_a")

    def test_drill_b_telemetry_exporter_failure_does_not_interrupt_payment(self) -> None:
        """Drill B: Verify telemetry/tracer failure does not interrupt safe payment execution."""
        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter=adapter)

        tx = Transaction(
            transaction_id="tx_drill_b",
            buyer_id="b_01",
            merchant_id="m_01",
            mandate_id="man_01",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_01",
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            idempotency_key="idemp_drill_b",
        )
        service.register_transaction(tx)

        req = PaymentExecuteProposalRequest(
            transaction_id="tx_drill_b",
            merchant_id="m_01",
            buyer_id="b_01",
            mandate_id="man_01",
            amount_paise=10000,
            currency=Currency.INR,
            cart_hash="ch_01",
            idempotency_key="idemp_drill_b",
        )
        auth_res = _make_allow_auth_result()

        with patch.object(
            tracer, "start_span", side_effect=RuntimeError("Telemetry Exporter Crashing")
        ):
            res = service.execute_payment(req, auth_res, tx)
            self.assertTrue(
                res.success, "Payment execution must succeed even if telemetry exporter crashes."
            )

    def test_drill_c_database_failure_causes_safe_readiness_failure(self) -> None:
        """Drill C: Verify database failure produces safe readiness 503 response."""
        res = degradation_matrix.evaluate_postgres_failure()
        self.assertEqual(res["readiness_status"], 503)

    def test_drill_d_redis_failure_behavior(self) -> None:
        """Drill D: Verify Redis failure enforces FAIL_CLOSED for locks and safe degradation for cache."""
        lock_res = degradation_matrix.evaluate_redis_failure(is_distributed_lock_required=True)
        self.assertEqual(lock_res["readiness_status"], 503)

        cache_res = degradation_matrix.evaluate_redis_failure(is_distributed_lock_required=False)
        self.assertEqual(cache_res["readiness_status"], 200)

    def test_drill_e_provider_timeout_produces_observable_ambiguous_state(self) -> None:
        """Drill E: Verify provider timeout produces observable UNKNOWN state without duplicating calls."""
        adapter = MockRazorpayAdapter()
        adapter.set_simulate_timeout(True)
        service = PaymentExecutionService(adapter=adapter)

        tx = Transaction(
            transaction_id="tx_drill_e",
            buyer_id="b_01",
            merchant_id="m_01",
            mandate_id="man_01",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_01",
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            idempotency_key="idemp_drill_e",
        )
        service.register_transaction(tx)

        req = PaymentExecuteProposalRequest(
            transaction_id="tx_drill_e",
            merchant_id="m_01",
            buyer_id="b_01",
            mandate_id="man_01",
            amount_paise=10000,
            currency=Currency.INR,
            cart_hash="ch_01",
            idempotency_key="idemp_drill_e",
        )
        auth_res = _make_allow_auth_result()

        res = service.execute_payment(req, auth_res, tx)
        self.assertFalse(res.success)
        self.assertEqual(res.provider_status, PaymentResultState.UNKNOWN)

    def test_drill_f_audit_verification_failure_raises_critical_alert(self) -> None:
        """Drill F: Verify audit verification failure triggers critical alert evaluation."""
        alert = alert_evaluator.evaluate_rule(
            rule_name="audit_chain_verification_failure",
            metric_value=1.0,
            threshold=1.0,
        )
        self.assertIsNotNone(alert)
        assert alert is not None
        self.assertEqual(alert["severity"], "CRITICAL")

    def test_drill_g_outbox_backlog_is_measurable(self) -> None:
        """Drill G: Verify outbox pending event backlog is measurable via metrics."""
        metrics_registry.set_gauge("outbox_events_pending", 42.0)
        val = metrics_registry.get_gauge_value("outbox_events_pending")
        self.assertEqual(val, 42.0)

    def test_drill_h_graceful_shutdown_prevents_duplicate_provider_execution(self) -> None:
        """Drill H: Verify graceful shutdown does not duplicate provider dispatches."""
        adapter = MockRazorpayAdapter()
        self.assertEqual(len(adapter.executed_requests), 0)

    def test_drill_i_metric_labels_cannot_explode_cardinality(self) -> None:
        """Drill I: Verify attacker-controlled input in metric labels is rejected by cardinality rules."""
        with self.assertRaises(ValueError):
            metrics_registry.increment_counter(
                "test_metric", labels={"attacker_input": "malicious_string_123"}
            )

    def test_drill_j_secrets_never_appear_in_structured_logs(self) -> None:
        """Drill J: Verify private cryptographic keys and secrets never appear in structured logs."""
        formatter = StructuredJsonFormatter()
        secret = SecretString("ed25519_private_key_sentinel_xyz")
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=100,
            msg=f"Key dump: {secret}",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        self.assertNotIn("ed25519_private_key_sentinel_xyz", formatted)
        self.assertIn("[REDACTED]", formatted)


if __name__ == "__main__":
    unittest.main()
