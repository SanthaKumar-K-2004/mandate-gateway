"""
Mandate Gateway — Production Alerting Rules & Evaluation Engine
Milestone M13 — SRE Controls Foundation

Defines production alert specifications and rule evaluation logic for critical subsystem failures.
"""

from __future__ import annotations

import dataclasses
import time
from typing import Any, Dict, List, Optional


@dataclasses.dataclass(frozen=True)
class AlertRule:
    name: str
    severity: str  # CRITICAL, HIGH, WARNING
    trigger_condition: str
    measurement_window: str
    recommended_action: str
    runbook_reference: str


# 10 Production Alert Rule Specifications
ALERT_RULES: List[AlertRule] = [
    AlertRule(
        name="audit_chain_verification_failure",
        severity="CRITICAL",
        trigger_condition="audit_chain_verification_failures_total > 0",
        measurement_window="1m",
        recommended_action=(
            "Halt audit writes, inspect tampered audit ledger records, "
            "execute integrity verification."
        ),
        runbook_reference="RUNBOOK_F_AUDIT_VERIFICATION_FAILURE.md",
    ),
    AlertRule(
        name="receipt_signature_verification_failure",
        severity="CRITICAL",
        trigger_condition="receipt_verification_failures_total > 0",
        measurement_window="1m",
        recommended_action=(
            "Inspect public key rotation, verify Ed25519 key store integrity, "
            "check receipt payload signatures."
        ),
        runbook_reference="RUNBOOK_G_RECEIPT_VERIFICATION_FAILURE.md",
    ),
    AlertRule(
        name="execution_unknown_backlog",
        severity="HIGH",
        trigger_condition="payment_execution_unknown_total > 5 within 5m",
        measurement_window="5m",
        recommended_action="Check Razorpay provider connection, trigger automatic status reconciliation daemon.",
        runbook_reference="RUNBOOK_B_PROVIDER_TIMEOUT.md",
    ),
    AlertRule(
        name="stuck_executing_transaction_age",
        severity="HIGH",
        trigger_condition="transactions in EXECUTING state for > 300s",
        measurement_window="5m",
        recommended_action="Execute recovery engine scan, reconcile provider status, transition to terminal state.",
        runbook_reference="RUNBOOK_A_STUCK_EXECUTING.md",
    ),
    AlertRule(
        name="outbox_backlog_critical",
        severity="HIGH",
        trigger_condition="outbox_events_pending > 100 or outbox_oldest_pending_age > 60s",
        measurement_window="2m",
        recommended_action="Check outbox worker process status, verify database pool availability.",
        runbook_reference="RUNBOOK_E_OUTBOX_BACKLOG.md",
    ),
    AlertRule(
        name="database_connection_exhaustion",
        severity="CRITICAL",
        trigger_condition="active_db_connections >= pool_max_size",
        measurement_window="1m",
        recommended_action=(
            "Inspect connection leak traces, increase connection pool, "
            "scale database read replicas."
        ),
        runbook_reference="RUNBOOK_H_DATABASE_POOL_EXHAUSTION.md",
    ),
    AlertRule(
        name="provider_failure_rate_high",
        severity="HIGH",
        trigger_condition="payment_execution_failure_total / payment_execution_total > 10% in 5m",
        measurement_window="5m",
        recommended_action=(
            "Inspect provider response status codes, verify API credentials, "
            "open incident with provider."
        ),
        runbook_reference="RUNBOOK_I_PROVIDER_ELEVATED_FAILURE_RATE.md",
    ),
    AlertRule(
        name="provider_latency_critical",
        severity="HIGH",
        trigger_condition="provider_latency p99 > 2000ms",
        measurement_window="5m",
        recommended_action="Check provider gateway status, activate fallback reconciliation queue.",
        runbook_reference="RUNBOOK_I_PROVIDER_ELEVATED_FAILURE_RATE.md",
    ),
    AlertRule(
        name="webhook_signature_attack_rate",
        severity="HIGH",
        trigger_condition="webhook_signature_failures_total > 20 in 1m",
        measurement_window="1m",
        recommended_action="Enable WAF rate limiting on webhook endpoint, verify webhook secret rotation.",
        runbook_reference="RUNBOOK_I_PROVIDER_ELEVATED_FAILURE_RATE.md",
    ),
    AlertRule(
        name="recovery_failure_rate",
        severity="HIGH",
        trigger_condition="transaction_recovery_total - transaction_recovery_success_total > 3 in 5m",
        measurement_window="5m",
        recommended_action="Inspect recovery worker logs, verify provider status API availability.",
        runbook_reference="RUNBOOK_A_STUCK_EXECUTING.md",
    ),
]


class AlertEvaluator:
    """Production Alert Rule Evaluation & Deduplication Engine."""

    def __init__(self) -> None:
        self._last_alerted: Dict[str, float] = {}
        self._cooldown_seconds: float = 60.0  # 1-minute deduplication window
        self._active_alerts: Dict[str, Dict[str, Any]] = {}

    def evaluate_rule(
        self,
        rule_name: str,
        metric_value: float,
        threshold: float,
        category: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Evaluates an alert rule and returns alert payload if triggered and not deduplicated."""
        rule = next((r for r in ALERT_RULES if r.name == rule_name), None)
        severity = rule.severity if rule else "CRITICAL"

        if metric_value >= threshold:
            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            alert_id = f"alert_{rule_name}"

            if alert_id in self._active_alerts:
                existing = self._active_alerts[alert_id]
                existing["last_detected_at"] = now_iso
                existing["metric_value"] = metric_value
                if context:
                    existing["context"].update(context)
                return existing

            alert = {
                "alert_id": alert_id,
                "rule_name": rule_name,
                "category": category or rule_name,
                "severity": severity,
                "status": "ACTIVE",
                "first_detected_at": now_iso,
                "last_detected_at": now_iso,
                "metric_value": metric_value,
                "threshold": threshold,
                "context": context or {},
                "trigger_condition": (
                    rule.trigger_condition if rule else f"{rule_name} >= {threshold}"
                ),
                "recommended_action": rule.recommended_action if rule else "Inspect system logs",
                "runbook_reference": (
                    rule.runbook_reference if rule else "RUNBOOK_A_STUCK_EXECUTING.md"
                ),
            }
            self._active_alerts[alert_id] = alert
            return alert
        return None

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Returns list of currently active alert objects."""
        return list(self._active_alerts.values())

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolves an active alert by alert_id."""
        if alert_id in self._active_alerts:
            self._active_alerts.pop(alert_id)
            return True
        return False

    def clear_alerts(self) -> None:
        """Clears all active alerts and history (for test isolation)."""
        self._active_alerts.clear()
        self._last_alerted.clear()


# Global singleton alert evaluator
alert_evaluator = AlertEvaluator()
