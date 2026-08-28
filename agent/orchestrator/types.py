"""
S03.2 — End-to-End Orchestrator Data Contracts.

Defines input request DTOs and complete execution output results (Section 24, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from agent.explainability.types import DecisionTraceReport
from apps.api.contracts.audit import AuditEventResponse, ReceiptResponse
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteResponse
from apps.api.domain.execution import ExecutionResult
from apps.api.domain.types import Currency, PolicyDecision, RejectionReason, TransactionState


class OrchestratorExecutionRequest(BaseModel):
    """Input payload to trigger an end-to-end commerce intent workflow."""

    user_intent_text: str = Field(..., min_length=1, max_length=1000, description="Raw user prompt/intent.")
    buyer_id: str = Field(..., min_length=1, description="Buyer identity UUID.")
    mandate_id: str = Field(..., min_length=1, description="Buyer mandate ID.")
    merchant_id: str = Field(..., min_length=1, description="Merchant identity ID.")
    idempotency_key: str = Field(..., min_length=1, description="Idempotency key.")


class EndToEndExecutionResult(BaseModel):
    """Comprehensive result object returned by the End-to-End Commerce Orchestrator."""

    transaction_id: str
    buyer_id: str
    merchant_id: str
    mandate_id: str
    overall_decision: PolicyDecision
    transaction_state: TransactionState
    amount_paise: int
    currency: Currency
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    authorization_result: AuthorizationResult | None = None
    execution_result: ExecutionResult | None = None
    audit_events: list[AuditEventResponse] = Field(default_factory=list)
    receipt: ReceiptResponse | None = None
    decision_trace_report: DecisionTraceReport | None = None
    formatted_text_trace: str | None = None
    executed_at: datetime
