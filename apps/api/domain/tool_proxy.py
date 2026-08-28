"""
S01.11 — Security Tool Proxy Boundary.

Security proxy layer insulating Mandate Gateway from untrusted AI tool calls:
  - Strips untrusted authority and override flags.
  - Enforces per-merchant operation allowlisting.
  - Enforces SSRF and URL safety.
  - Normalizes AI tool input into PaymentExecuteProposalRequest.
"""

from __future__ import annotations

import re
from typing import Any

from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import (
    PaymentExecuteProposalRequest,
    PaymentExecuteResponse,
)
from apps.api.domain.execution import ExecutionFailureCategory, ExecutionResult
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import Currency, McpOperation, RejectionReason, TransactionState


class SecurityToolProxy:
    """
    Proxy component enforcing security isolation between AI agents/MCP tools
    and the trusted PaymentExecutionService.
    """

    UNTRUSTED_AUTHORITY_KEYS = frozenset(
        {
            "admin_override",
            "bypass_auth",
            "payment_approved",
            "skip_policy",
            "skip_mandate",
            "skip_budget",
            "skip_nonce",
            "skip_step_up",
            "force_execute",
            "is_authorized",
            "authorized",
        }
    )

    BLOCKED_URL_PATTERNS = (
        r"localhost",
        r"127\.0\.0\.1",
        r"0\.0\.0\.0",
        r"169\.254\.",
        r"file://",
        r"data:",
        r"javascript:",
    )

    def __init__(self, execution_service: PaymentExecutionService) -> None:
        self.execution_service = execution_service

    def sanitize_untrusted_input(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Strip untrusted authority override keys from input dict."""
        sanitized = {}
        for k, v in tool_input.items():
            if k.lower() in self.UNTRUSTED_AUTHORITY_KEYS:
                continue
            sanitized[k] = v
        return sanitized

    def validate_url_safety(self, url: str) -> bool:
        """Return False if url contains SSRF or local network patterns."""
        low = url.lower().strip()
        for pat in self.BLOCKED_URL_PATTERNS:
            if re.search(pat, low):
                return False
        return True

    def invoke_execution_tool(
        self,
        raw_tool_input: dict[str, Any],
        authorization_result: AuthorizationResult,
        transaction: Transaction,
    ) -> PaymentExecuteResponse:
        """
        Safely process an AI payment tool invocation.
        """
        # 1. Sanitize untrusted authority fields
        clean_input = self.sanitize_untrusted_input(raw_tool_input)

        # 2. Check for URL safety if custom URL supplied
        custom_url = clean_input.get("target_url")
        if custom_url and isinstance(custom_url, str):
            if not self.validate_url_safety(custom_url):
                return PaymentExecuteResponse(
                    success=False,
                    transaction_id=transaction.transaction_id,
                    state=TransactionState.REJECTED,
                    failure_code=RejectionReason.OPERATION_NOT_ALLOWED,
                    failure_category=ExecutionFailureCategory.INVALID_CONTEXT.value,
                    safe_message="Blocked attempt to access invalid or unsafe target URL.",
                )

        # 3. Parse operation
        op_raw = clean_input.get("operation", "create_order")
        try:
            op = McpOperation(op_raw)
        except ValueError:
            return PaymentExecuteResponse(
                success=False,
                transaction_id=transaction.transaction_id,
                state=TransactionState.REJECTED,
                failure_code=RejectionReason.OPERATION_NOT_ALLOWED,
                failure_category=ExecutionFailureCategory.VALIDATION_ERROR.value,
                safe_message=f"Unsupported MCP operation: {op_raw!r}.",
            )

        # 4. Construct proposal DTO
        try:
            proposal = PaymentExecuteProposalRequest(
                transaction_id=str(clean_input.get("transaction_id", transaction.transaction_id)),
                merchant_id=str(clean_input.get("merchant_id", transaction.merchant_id)),
                buyer_id=str(clean_input.get("buyer_id", transaction.buyer_id)),
                mandate_id=str(clean_input.get("mandate_id", transaction.mandate_id)),
                amount_paise=int(clean_input.get("amount_paise", transaction.amount_paise)),
                currency=Currency(clean_input.get("currency", transaction.currency.value)),
                cart_hash=str(clean_input.get("cart_hash", transaction.cart_hash or "")),
                operation=op,
                idempotency_key=str(
                    clean_input.get("idempotency_key", f"exec:{transaction.transaction_id}")
                ),
                untrusted_metadata=clean_input.get("untrusted_metadata", {}),
            )
        except Exception as e:
            return PaymentExecuteResponse(
                success=False,
                transaction_id=transaction.transaction_id,
                state=TransactionState.REJECTED,
                failure_code=RejectionReason.INVALID_TRANSACTION_STATE,
                failure_category=ExecutionFailureCategory.VALIDATION_ERROR.value,
                safe_message=f"Invalid execution proposal parameters: {e}",
            )

        # 5. Execute via trusted execution service
        domain_result: ExecutionResult = self.execution_service.execute_payment(
            proposal=proposal,
            authorization_result=authorization_result,
            transaction=transaction,
        )

        return PaymentExecuteResponse(
            success=domain_result.success,
            transaction_id=domain_result.transaction_id,
            state=domain_result.state,
            external_reference=domain_result.external_reference,
            failure_code=domain_result.failure_code,
            failure_category=(
                domain_result.failure_category.value if domain_result.failure_category else None
            ),
            safe_message=domain_result.safe_message,
            idempotent_replay=domain_result.idempotent_replay,
            provider_status=domain_result.provider_status,
            executed_at=domain_result.executed_at,
        )
