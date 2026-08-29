"""
S02.8 — Decision Trace & Explainability Engine.

Generates deterministic, human-readable ASCII decision traces and structured DTO reports
for transaction authorization & execution lifecycles (Section 22 & Section 24, PROJECT_CONTEXT.md).

Core Invariant:
    Zero LLM authorization. Traces reflect strictly trusted gateway authorization decisions.
"""

from __future__ import annotations

import re
from typing import Any

from agent.explainability.errors import ExplainabilityErrorCode, ExplainabilityError
from agent.explainability.types import CheckTraceStep, DecisionTraceReport
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.execution_engine import ExecutionResult
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import PolicyDecision, RejectionReason

_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|password|bearer|auth[_-]?header|private[_-]?key)\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?"
)


def sanitize_trace_text(text: str) -> str:
    """Sanitize any sensitive credentials or secret headers in trace text."""
    if not text:
        return ""
    return _SECRET_KEY_PATTERN.sub(r"\1: [REDACTED]", text)


class ExplainabilityEngine:
    """
    Deterministic Explainability & Decision Trace Engine.
    """

    def generate_trace(
        self,
        transaction_id: str,
        authorization_result: AuthorizationResult,
        execution_result: ExecutionResult | None = None,
        transaction: Transaction | None = None,
        audit_event_id: str | None = None,
        action_receipt_id: str | None = None,
    ) -> DecisionTraceReport:
        """
        Generate a comprehensive DecisionTraceReport and formatted ASCII trace string.
        """
        if not transaction_id or not transaction_id.strip():
            raise ExplainabilityError(
                code=ExplainabilityErrorCode.INVALID_TRACE_DATA,
                message="Transaction ID must be a non-empty string.",
            )

        if authorization_result is None:
            raise ExplainabilityError(
                code=ExplainabilityErrorCode.INVALID_TRACE_DATA,
                message="Authorization result cannot be None.",
            )

        # Extract metadata
        mandate_id = transaction.mandate_id if transaction else None
        merchant_id = transaction.merchant_id if transaction else None
        buyer_id = transaction.buyer_id if transaction else None

        overall_decision = authorization_result.decision
        control_steps: list[dict[str, Any]] = []
        failed_steps: list[CheckTraceStep] = []

        for outcome in authorization_result.control_outcomes:
            step = CheckTraceStep(
                control_name=outcome.control_name,
                passed=outcome.passed,
                decision=outcome.decision,
                rejection_reason=outcome.rejection_reason,
                detail=sanitize_trace_text(outcome.detail or ""),
            )
            control_steps.append(
                {
                    "control_name": step.control_name,
                    "passed": step.passed,
                    "decision": step.decision.value,
                    "rejection_reason": (
                        step.rejection_reason.value if step.rejection_reason else None
                    ),
                    "detail": step.detail,
                    "evaluated_at": step.evaluated_at.isoformat(),
                }
            )
            if not step.passed or step.decision != PolicyDecision.ALLOW:
                failed_steps.append(step)

        # Razorpay execution status resolution
        if execution_result:
            if execution_result.success:
                razorpay_status = f"EXECUTED ({execution_result.external_reference or 'SUCCESS'})"
            elif execution_result.provider_status:
                razorpay_status = f"FAILED ({execution_result.provider_status.value})"
            else:
                razorpay_status = "FAILED"
        elif overall_decision == PolicyDecision.STEP_UP_REQUIRED:
            razorpay_status = "NOT ATTEMPTED (AWAITING CONFIRMATION)"
        elif overall_decision == PolicyDecision.REJECT:
            razorpay_status = "NOT ATTEMPTED"
        else:
            razorpay_status = "PENDING EXECUTION"

        # Summary reason resolution
        if overall_decision == PolicyDecision.ALLOW:
            summary_reason = "All mandatory authorization constraints satisfied."
        elif overall_decision == PolicyDecision.STEP_UP_REQUIRED:
            summary_reason = "Autonomous spend limit exceeded. Human step-up confirmation required."
        else:
            if failed_steps:
                first_failed = failed_steps[0]
                reason_str = (
                    first_failed.rejection_reason.value
                    if first_failed.rejection_reason
                    else (first_failed.detail or "Constraint failed")
                )
                summary_reason = (
                    f"Security control '{first_failed.control_name}' failed: {reason_str}"
                )
            else:
                summary_reason = "Authorization failed closed due to policy rejection."

        # Format ASCII trace
        ascii_trace = self._format_ascii_trace(
            transaction_id=transaction_id,
            overall_decision=overall_decision,
            control_outcomes=authorization_result.control_outcomes,
            failed_steps=failed_steps,
            summary_reason=summary_reason,
            razorpay_status=razorpay_status,
        )

        return DecisionTraceReport(
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            overall_decision=overall_decision,
            summary_reason=summary_reason,
            control_steps=control_steps,
            razorpay_execution_status=razorpay_status,
            audit_event_id=audit_event_id,
            action_receipt_id=action_receipt_id,
            formatted_text_trace=ascii_trace,
        )

    def _format_ascii_trace(
        self,
        transaction_id: str,
        overall_decision: PolicyDecision,
        control_outcomes: list[Any],
        failed_steps: list[CheckTraceStep],
        summary_reason: str,
        razorpay_status: str,
    ) -> str:
        """Format a human-readable ASCII decision trace string matching Section 22 spec."""
        lines = [f"TRANSACTION {transaction_id}", ""]

        if overall_decision == PolicyDecision.ALLOW:
            for outcome in control_outcomes:
                lines.append(f"✓ {outcome.control_name.replace('_', ' ').capitalize()} valid")
            lines.append("")
            lines.append("DECISION: AUTO_EXECUTE")
            lines.append("")
            lines.append("Reason:")
            lines.append(summary_reason)
            lines.append("")
            lines.append(f"Razorpay execution: {razorpay_status}")
        elif overall_decision == PolicyDecision.STEP_UP_REQUIRED:
            lines.append("DECISION: STEP_UP_REQUIRED")
            lines.append("")
            lines.append("Pending check:")
            lines.append("STEP_UP_AUTHORIZATION")
            lines.append("")
            lines.append("Reason:")
            lines.append(summary_reason)
            lines.append("")
            lines.append(f"Razorpay execution: {razorpay_status}")
        else:
            lines.append("DECISION: REJECT")
            lines.append("")
            if failed_steps:
                lines.append("Failed check:")
                lines.append(failed_steps[0].control_name)
                lines.append("")
                lines.append("Reason:")
                lines.append(summary_reason)
            else:
                lines.append("Reason:")
                lines.append(summary_reason)
            lines.append("")
            lines.append(f"Razorpay execution: {razorpay_status}")

        return "\n".join(lines)
