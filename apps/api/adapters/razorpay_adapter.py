"""
S01.11 — Razorpay Adapter Boundary.

Clean interface and implementations for external Razorpay payment integration:
  - RazorpayAdapterInterface: Abstract provider protocol.
  - MockRazorpayAdapter: Deterministic mock provider for tests and failure injection.
  - RazorpayHttpAdapter: Production HTTP adapter with SSRF safety, timeout control,
    and credential redaction.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from apps.api.config.types import SecretString
from apps.api.domain.execution import (
    ExecutionFailureCategory,
    ExecutionResult,
    TrustedExecutionRequest,
)
from apps.api.domain.types import (
    McpOperation,
    PaymentResultState,
    RejectionReason,
    TransactionState,
)


class RazorpayAdapterInterface(ABC):
    """Abstract interface defining external Razorpay payment operations."""

    @abstractmethod
    def execute_payment(self, request: TrustedExecutionRequest) -> ExecutionResult:
        """Execute payment operation against Razorpay."""

    @abstractmethod
    def fetch_payment_status(self, payment_id: str) -> ExecutionResult:
        """Fetch payment status from Razorpay."""


class MockRazorpayAdapter(RazorpayAdapterInterface):
    """
    Deterministic mock Razorpay adapter for unit tests, integration tests,
    concurrency tests, and failure injection.
    """

    def __init__(self) -> None:
        self.executed_requests: list[TrustedExecutionRequest] = []
        self.reconciled_requests: list[str] = []
        self._next_failure_category: ExecutionFailureCategory | None = None
        self._next_failure_reason: RejectionReason | None = None
        self._next_failure_message: str | None = None
        self._raise_timeout: bool = False
        self._raise_connection_error: bool = False
        self._custom_response: ExecutionResult | None = None
        self._reconcile_status: PaymentResultState = PaymentResultState.SUCCESS
        self._reconcile_timeout: bool = False
        self._reconcile_malformed: bool = False

    def set_next_failure(
        self,
        category: ExecutionFailureCategory,
        reason: RejectionReason,
        message: str = "Simulated provider failure",
    ) -> None:
        """Configure mock to return a specific failure on next invocation."""
        self._next_failure_category = category
        self._next_failure_reason = reason
        self._next_failure_message = message

    def set_simulate_timeout(self, enabled: bool = True) -> None:
        """Configure mock to simulate a network timeout."""
        self._raise_timeout = enabled

    def set_simulate_connection_error(self, enabled: bool = True) -> None:
        """Configure mock to simulate a connection error."""
        self._raise_connection_error = enabled

    def set_custom_response(self, result: ExecutionResult) -> None:
        """Set an explicit custom ExecutionResult response."""
        self._custom_response = result

    def set_reconciliation_status(self, status: PaymentResultState) -> None:
        """Set the provider status returned during status reconciliation."""
        self._reconcile_status = status

    def set_reconciliation_timeout(self, enabled: bool = True) -> None:
        """Configure status reconciliation to time out."""
        self._reconcile_timeout = enabled

    def set_reconciliation_malformed(self, enabled: bool = True) -> None:
        """Configure status reconciliation to return malformed/invalid data."""
        self._reconcile_malformed = enabled

    def reset(self) -> None:
        """Reset mock state and history."""
        self.executed_requests.clear()
        self.reconciled_requests.clear()
        self._next_failure_category = None
        self._next_failure_reason = None
        self._next_failure_message = None
        self._raise_timeout = False
        self._raise_connection_error = False
        self._custom_response = None
        self._reconcile_status = PaymentResultState.SUCCESS
        self._reconcile_timeout = False
        self._reconcile_malformed = False

    def execute_payment(self, request: TrustedExecutionRequest) -> ExecutionResult:
        """Simulate payment execution deterministically."""
        self.executed_requests.append(request)

        if self._custom_response is not None:
            return self._custom_response

        if self._raise_timeout:
            return ExecutionResult(
                success=False,
                transaction_id=request.transaction_id,
                state=TransactionState.EXECUTING,
                failure_code=RejectionReason.AUTHORIZATION_EXPIRED,
                failure_category=ExecutionFailureCategory.TIMEOUT,
                safe_message="Razorpay gateway connection timed out.",
                provider_status=PaymentResultState.UNKNOWN,
            )

        if self._raise_connection_error:
            return ExecutionResult(
                success=False,
                transaction_id=request.transaction_id,
                state=TransactionState.EXECUTING,
                failure_code=RejectionReason.AUTHORIZATION_EXPIRED,
                failure_category=ExecutionFailureCategory.CONNECTION_FAILED,
                safe_message="Failed to connect to Razorpay payment gateway.",
                provider_status=PaymentResultState.UNKNOWN,
            )

        if self._next_failure_category is not None:
            cat = self._next_failure_category
            reason = self._next_failure_reason or RejectionReason.METHOD_NOT_AUTHORIZED
            msg = self._next_failure_message or "Simulated provider failure"
            return ExecutionResult(
                success=False,
                transaction_id=request.transaction_id,
                state=TransactionState.FAILURE,
                failure_code=reason,
                failure_category=cat,
                safe_message=msg,
                provider_status=PaymentResultState.FAILED,
            )

        # Default happy-path simulation
        if request.operation is McpOperation.CREATE_ORDER:
            ext_ref = f"order_simulated_{request.transaction_id[:8]}"
        elif request.operation is McpOperation.CREATE_PAYMENT_LINK:
            ext_ref = f"plink_simulated_{request.transaction_id[:8]}"
        else:
            ext_ref = f"pay_simulated_{request.transaction_id[:8]}"

        return ExecutionResult(
            success=True,
            transaction_id=request.transaction_id,
            state=TransactionState.SUCCESS,
            external_reference=ext_ref,
            safe_message="Payment order created successfully.",
            provider_status=PaymentResultState.SUCCESS,
            raw_response_redacted={
                "id": ext_ref,
                "entity": "order",
                "amount": request.amount_paise,
                "currency": request.currency.value,
                "status": "created",
            },
        )

    def fetch_payment_status(self, payment_id: str) -> ExecutionResult:
        """Simulate fetching payment status from Razorpay."""
        self.reconciled_requests.append(payment_id)

        if self._reconcile_timeout:
            return ExecutionResult(
                success=False,
                transaction_id="tx-fetch",
                state=TransactionState.EXECUTING,
                external_reference=payment_id,
                failure_code=RejectionReason.AUTHORIZATION_EXPIRED,
                failure_category=ExecutionFailureCategory.TIMEOUT,
                safe_message="Status reconciliation request timed out.",
                provider_status=PaymentResultState.UNKNOWN,
            )

        if self._reconcile_malformed:
            return ExecutionResult(
                success=False,
                transaction_id="tx-fetch",
                state=TransactionState.EXECUTING,
                external_reference=payment_id,
                failure_code=RejectionReason.METHOD_NOT_AUTHORIZED,
                failure_category=ExecutionFailureCategory.UNKNOWN_PROVIDER_ERROR,
                safe_message="Malformed response received during status reconciliation.",
                provider_status=PaymentResultState.UNKNOWN,
            )

        is_success = self._reconcile_status == PaymentResultState.SUCCESS
        state = TransactionState.SUCCESS if is_success else TransactionState.FAILURE
        return ExecutionResult(
            success=is_success,
            transaction_id="tx-fetch",
            state=state,
            external_reference=payment_id,
            safe_message=f"Reconciled status for {payment_id}: {self._reconcile_status.value}",
            provider_status=self._reconcile_status,
            raw_response_redacted={
                "id": payment_id,
                "entity": "payment",
                "status": "captured" if is_success else "failed",
            },
        )


class RazorpayHttpAdapter(RazorpayAdapterInterface):
    """
    Production HTTP Razorpay adapter using standard Python urllib.

    Enforces:
      - SSRF protection (whitelisted domain https://api.razorpay.com).
      - Strict timeouts (5 seconds).
      - Credential security via SecretString (redacted in exception messages & logs).
      - Comprehensive error classification.
    """

    ALLOWED_BASE_URL = "https://api.razorpay.com/v1"

    def __init__(
        self,
        key_id: SecretString,
        key_secret: SecretString,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._key_id = key_id
        self._key_secret = key_secret
        self._timeout = timeout_seconds

    def execute_payment(self, request: TrustedExecutionRequest) -> ExecutionResult:
        """Execute payment operation against live Razorpay REST API."""
        if request.operation is McpOperation.CREATE_ORDER:
            endpoint = f"{self.ALLOWED_BASE_URL}/orders"
        elif request.operation is McpOperation.CREATE_PAYMENT_LINK:
            endpoint = f"{self.ALLOWED_BASE_URL}/payment_links"
        else:
            endpoint = f"{self.ALLOWED_BASE_URL}/payments"

        # SSRF Enforcement
        if not endpoint.startswith(self.ALLOWED_BASE_URL):
            return ExecutionResult(
                success=False,
                transaction_id=request.transaction_id,
                state=TransactionState.FAILURE,
                failure_code=RejectionReason.OPERATION_NOT_ALLOWED,
                failure_category=ExecutionFailureCategory.INVALID_CONTEXT,
                safe_message="Target URL outside allowed Razorpay domain.",
                provider_status=PaymentResultState.FAILED,
            )

        payload = {
            "amount": request.amount_paise,
            "currency": request.currency.value,
            "receipt": request.transaction_id,
            "notes": {
                "mandate_id": request.mandate_id,
                "cart_hash": request.cart_hash,
            },
        }

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=data_bytes,
                method="POST",
                headers={"Content-Type": "application/json"},
            )

            # Inject basic auth safely without exposing credentials to caller or logs
            import base64

            creds = f"{self._key_id.get_secret_value()}:{self._key_secret.get_secret_value()}"
            auth_header = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
            req.add_header("Authorization", f"Basic {auth_header}")

            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))

            ext_id = body.get("id", f"rzp_{request.transaction_id[:8]}")
            return ExecutionResult(
                success=True,
                transaction_id=request.transaction_id,
                state=TransactionState.SUCCESS,
                external_reference=ext_id,
                safe_message=f"Razorpay operation {request.operation.value} succeeded.",
                provider_status=PaymentResultState.SUCCESS,
                raw_response_redacted={"id": ext_id, "status": body.get("status", "created")},
            )

        except urllib.error.HTTPError as err:
            err_code = err.code
            if err_code in (401, 403):
                cat = ExecutionFailureCategory.AUTHENTICATION_ERROR
                reason = RejectionReason.METHOD_NOT_AUTHORIZED
                msg = "Razorpay authentication failed."
            elif err_code == 400:
                cat = ExecutionFailureCategory.VALIDATION_ERROR
                reason = RejectionReason.INVALID_AMOUNT
                msg = "Razorpay request validation failed."
            elif err_code == 429:
                cat = ExecutionFailureCategory.RATE_LIMIT_EXCEEDED
                reason = RejectionReason.AUTONOMOUS_EXECUTION_DISABLED
                msg = "Razorpay rate limit exceeded."
            else:
                cat = ExecutionFailureCategory.PROVIDER_REJECTED
                reason = RejectionReason.METHOD_NOT_AUTHORIZED
                msg = f"Razorpay API returned HTTP error {err_code}."

            return ExecutionResult(
                success=False,
                transaction_id=request.transaction_id,
                state=TransactionState.FAILURE,
                failure_code=reason,
                failure_category=cat,
                safe_message=msg,
                provider_status=PaymentResultState.FAILED,
            )

        except (urllib.error.URLError, TimeoutError, OSError) as err:
            is_timeout = "timed out" in str(err).lower() or isinstance(err, TimeoutError)
            cat = (
                ExecutionFailureCategory.TIMEOUT
                if is_timeout
                else ExecutionFailureCategory.CONNECTION_FAILED
            )
            msg = "Razorpay API request timed out." if is_timeout else "Razorpay connection error."

            return ExecutionResult(
                success=False,
                transaction_id=request.transaction_id,
                state=TransactionState.FAILURE,
                failure_code=RejectionReason.AUTHORIZATION_EXPIRED,
                failure_category=cat,
                safe_message=msg,
                provider_status=PaymentResultState.UNKNOWN,
            )

        except Exception:
            return ExecutionResult(
                success=False,
                transaction_id=request.transaction_id,
                state=TransactionState.FAILURE,
                failure_code=RejectionReason.METHOD_NOT_AUTHORIZED,
                failure_category=ExecutionFailureCategory.UNKNOWN_PROVIDER_ERROR,
                safe_message="An unexpected error occurred during payment execution.",
                provider_status=PaymentResultState.UNKNOWN,
            )

    def fetch_payment_status(self, payment_id: str) -> ExecutionResult:
        """Fetch payment status from live Razorpay REST API."""
        endpoint = f"{self.ALLOWED_BASE_URL}/payments/{payment_id}"
        try:
            req = urllib.request.Request(endpoint, method="GET")
            import base64

            creds = f"{self._key_id.get_secret_value()}:{self._key_secret.get_secret_value()}"
            auth_header = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
            req.add_header("Authorization", f"Basic {auth_header}")

            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))

            status_str = body.get("status", "captured")
            p_status = (
                PaymentResultState.SUCCESS
                if status_str == "captured"
                else PaymentResultState.PENDING
            )

            return ExecutionResult(
                success=True,
                transaction_id="tx-fetch",
                state=TransactionState.SUCCESS,
                external_reference=payment_id,
                safe_message=f"Fetched payment {payment_id}.",
                provider_status=p_status,
                raw_response_redacted={"id": payment_id, "status": status_str},
            )

        except Exception:
            return ExecutionResult(
                success=False,
                transaction_id="tx-fetch",
                state=TransactionState.FAILURE,
                failure_code=RejectionReason.METHOD_NOT_AUTHORIZED,
                failure_category=ExecutionFailureCategory.UNKNOWN_PROVIDER_ERROR,
                safe_message=f"Failed to fetch status for payment {payment_id}.",
                provider_status=PaymentResultState.UNKNOWN,
            )
