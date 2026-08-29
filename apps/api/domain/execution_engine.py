"""
S01.11 — Payment Execution Engine & Gateway Boundary.

Core execution service implementing the fail-closed payment execution boundary:
  - Verifies S01.5 AuthorizationResult (ALLOW required).
  - Enforces strict context integrity (amount, currency, merchant, buyer, mandate, cart hash).
  - Enforces per-merchant operation allowlisting.
  - Constructs TrustedExecutionRequest using authoritative context.
  - Atomic state claim (AUTHORIZED → EXECUTING) under RLock.
  - Idempotency & double-execution prevention.
  - Adapter invocation & error mapping.
  - Transaction state transitions (EXECUTING → SUCCESS → COMMITTED or FAILURE → ROLLED_BACK).
  - Safe audit evidence generation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Dict, Optional, TYPE_CHECKING

from apps.api.adapters.razorpay_adapter import RazorpayAdapterInterface
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.execution import (
    ExecutionAuditEvidence,
    ExecutionFailureCategory,
    ExecutionResult,
    TrustedExecutionRequest,
)
from apps.api.domain.transaction import Transaction
from apps.api.domain.transaction_engine import transition_transaction
from apps.api.domain.types import (
    McpOperation,
    PaymentResultState,
    PolicyDecision,
    RejectionReason,
    TransactionState,
)

if TYPE_CHECKING:
    from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class PaymentExecutionService:
    """
    Thread-safe Payment Execution Boundary service.

    Enforces all pre-execution security controls, transaction state transitions,
    idempotency guarantees, and provider invocation.
    """

    def __init__(self, adapter: RazorpayAdapterInterface) -> None:
        self.adapter = adapter
        self._lock = threading.RLock()
        # In-memory execution store for state tracking & idempotency
        self._transactions: Dict[str, Transaction] = {}
        self._results: Dict[str, ExecutionResult] = {}
        self._audit_events: list[ExecutionAuditEvidence] = []

    def register_transaction(self, transaction: Transaction) -> None:
        """Register an authoritative transaction record in the engine."""
        with self._lock:
            self._transactions[transaction.transaction_id] = transaction

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Fetch transaction record by ID."""
        with self._lock:
            return self._transactions.get(transaction_id)

    def get_execution_result(self, transaction_id: str) -> Optional[ExecutionResult]:
        """Fetch cached execution result by transaction ID."""
        with self._lock:
            return self._results.get(transaction_id)

    def execute_payment(
        self,
        proposal: PaymentExecuteProposalRequest,
        authorization_result: AuthorizationResult,
        transaction: Transaction,
    ) -> ExecutionResult:
        """
        Execute payment following the complete S01.11 security boundary flow.

        1. Pre-execution authorization gate & context validation.
        2. Operation allowlist check.
        3. Idempotency check.
        4. Atomic transaction state claim (AUTHORIZED → EXECUTING).
        5. Trusted execution request construction.
        6. Provider invocation via Razorpay adapter.
        7. State transition & result recording.
        8. Audit evidence creation.
        """
        with self._lock:
            # Idempotency / Retry check:
            if transaction.transaction_id in self._results:
                existing_res = self._results[transaction.transaction_id]
                # If previous execution outcome was UNKNOWN, attempt status reconciliation!
                if existing_res.provider_status == PaymentResultState.UNKNOWN:
                    return self.reconcile_payment_status(transaction.transaction_id)

                return ExecutionResult(
                    success=existing_res.success,
                    transaction_id=existing_res.transaction_id,
                    state=existing_res.state,
                    external_reference=existing_res.external_reference,
                    failure_code=existing_res.failure_code,
                    failure_category=existing_res.failure_category,
                    safe_message=existing_res.safe_message,
                    idempotent_replay=True,
                    provider_status=existing_res.provider_status,
                    raw_response_redacted=existing_res.raw_response_redacted,
                    executed_at=existing_res.executed_at,
                )

            # Save active transaction
            self._transactions[transaction.transaction_id] = transaction

            # Pre-execution authorization & context verification
            auth_rej = self._verify_pre_execution_auth(authorization_result, transaction)
            if auth_rej:
                return auth_rej

            ctx_rej = self._verify_context_and_operation(proposal, transaction)
            if ctx_rej:
                return ctx_rej

            # ------------------------------------------------------------------
            # 4. Atomic Transaction State Claim (AUTHORIZED → EXECUTING)
            # ------------------------------------------------------------------
            if not transaction.is_executable():
                return self._reject_execution(
                    transaction=transaction,
                    reason=RejectionReason.INVALID_TRANSACTION_STATE,
                    category=ExecutionFailureCategory.INVALID_CONTEXT,
                    message=f"Transaction in state {transaction.state.value} cannot be executed.",
                )

            try:
                executing_tx = transition_transaction(
                    transaction,
                    TransactionState.EXECUTING,
                )
                self._transactions[executing_tx.transaction_id] = executing_tx
            except Exception as e:
                return self._reject_execution(
                    transaction=transaction,
                    reason=RejectionReason.INVALID_TRANSACTION_STATE,
                    category=ExecutionFailureCategory.INVALID_CONTEXT,
                    message=f"Failed to claim EXECUTING state: {e}",
                )

            # ------------------------------------------------------------------
            # 5. Trusted Execution Request Construction
            # ------------------------------------------------------------------
            trusted_request = TrustedExecutionRequest(
                transaction_id=executing_tx.transaction_id,
                merchant_id=executing_tx.merchant_id,
                buyer_id=executing_tx.buyer_id,
                mandate_id=executing_tx.mandate_id,
                amount_paise=executing_tx.amount_paise,
                currency=executing_tx.currency,
                cart_hash=executing_tx.cart_hash or proposal.cart_hash,
                operation=proposal.operation,
                authorization_reference=authorization_result.decision_trace.get(
                    "authorization_reference", f"auth_{executing_tx.transaction_id[:8]}"
                ),
                idempotency_key=f"exec:{executing_tx.transaction_id}",
            )

            # ------------------------------------------------------------------
            # 6. Provider Invocation (Razorpay Adapter)
            # ------------------------------------------------------------------
            provider_result = self.adapter.execute_payment(trusted_request)

            # ------------------------------------------------------------------
            # 7. Post-Execution State Transitions & Result Recording
            # ------------------------------------------------------------------
            if provider_result.success:
                # EXECUTING → SUCCESS → COMMITTED
                success_tx = transition_transaction(
                    executing_tx,
                    TransactionState.SUCCESS,
                    razorpay_order_id=provider_result.external_reference,
                )
                committed_tx = transition_transaction(
                    success_tx,
                    TransactionState.COMMITTED,
                )
                self._transactions[committed_tx.transaction_id] = committed_tx

                final_res = ExecutionResult(
                    success=True,
                    transaction_id=committed_tx.transaction_id,
                    state=TransactionState.COMMITTED,
                    external_reference=provider_result.external_reference,
                    safe_message=provider_result.safe_message,
                    provider_status=PaymentResultState.SUCCESS,
                    raw_response_redacted=provider_result.raw_response_redacted,
                    executed_at=provider_result.executed_at,
                )
            elif provider_result.provider_status == PaymentResultState.UNKNOWN:
                # UNKNOWN OUTCOME INVARIANT:
                # UNKNOWN ≠ SUCCESS, UNKNOWN ≠ DEFINITIVE FAILURE/ROLLBACK!
                # Transaction remains in EXECUTING state until status reconciliation.
                self._transactions[executing_tx.transaction_id] = executing_tx

                final_res = ExecutionResult(
                    success=False,
                    transaction_id=executing_tx.transaction_id,
                    state=TransactionState.EXECUTING,
                    external_reference=provider_result.external_reference,
                    failure_code=provider_result.failure_code
                    or RejectionReason.AUTHORIZATION_EXPIRED,
                    failure_category=provider_result.failure_category
                    or ExecutionFailureCategory.TIMEOUT,
                    safe_message=(
                        provider_result.safe_message
                        or "Payment outcome is UNKNOWN due to gateway timeout. Status reconciliation required."
                    ),
                    provider_status=PaymentResultState.UNKNOWN,
                    raw_response_redacted=provider_result.raw_response_redacted,
                    executed_at=provider_result.executed_at,
                )
            else:
                # EXECUTING → FAILURE → ROLLED_BACK (for definitive provider rejection / failure)
                failure_reason = (
                    provider_result.failure_code or RejectionReason.METHOD_NOT_AUTHORIZED
                )
                failure_tx = transition_transaction(
                    executing_tx,
                    TransactionState.FAILURE,
                )
                rolled_back_tx = transition_transaction(
                    failure_tx,
                    TransactionState.ROLLED_BACK,
                )
                self._transactions[rolled_back_tx.transaction_id] = rolled_back_tx

                final_res = ExecutionResult(
                    success=False,
                    transaction_id=rolled_back_tx.transaction_id,
                    state=TransactionState.ROLLED_BACK,
                    external_reference=provider_result.external_reference,
                    failure_code=failure_reason,
                    failure_category=provider_result.failure_category,
                    safe_message=provider_result.safe_message,
                    provider_status=provider_result.provider_status or PaymentResultState.FAILED,
                    raw_response_redacted=provider_result.raw_response_redacted,
                    executed_at=provider_result.executed_at,
                )

            # Save result for idempotency lookup
            self._results[transaction.transaction_id] = final_res

            # Record safe audit evidence
            self._audit_events.append(
                ExecutionAuditEvidence(
                    transaction_id=transaction.transaction_id,
                    merchant_id=transaction.merchant_id,
                    buyer_id=transaction.buyer_id,
                    mandate_id=transaction.mandate_id,
                    operation=proposal.operation.value,
                    amount_paise=transaction.amount_paise,
                    currency=transaction.currency.value,
                    authorization_reference=trusted_request.authorization_reference,
                    execution_result_success=final_res.success,
                    external_reference=final_res.external_reference,
                    failure_category=(
                        final_res.failure_category.value if final_res.failure_category else None
                    ),
                    provider_status=(
                        final_res.provider_status.value if final_res.provider_status else None
                    ),
                )
            )

            return final_res

    def reconcile_payment_status(
        self,
        transaction_id: str,
        external_reference: str | None = None,
    ) -> ExecutionResult:
        """
        Reconcile an in-flight or UNKNOWN transaction by querying provider status.

        1. If provider status is SUCCESS: transition EXECUTING → SUCCESS → COMMITTED.
        2. If provider status is FAILED / EXPIRED: transition EXECUTING → FAILURE → ROLLED_BACK.
        3. If provider status remains UNKNOWN / TIMEOUT: maintain EXECUTING state.
        """
        with self._lock:
            tx = self._transactions.get(transaction_id)
            if not tx:
                return ExecutionResult(
                    success=False,
                    transaction_id=transaction_id,
                    state=TransactionState.REJECTED,
                    failure_code=RejectionReason.INVALID_TRANSACTION_STATE,
                    failure_category=ExecutionFailureCategory.INVALID_CONTEXT,
                    safe_message=f"Transaction {transaction_id!r} not found for reconciliation.",
                )

            # If transaction is already COMMITTED or ROLLED_BACK, return cached result
            if tx.is_terminal():
                cached = self._results.get(transaction_id)
                if cached:
                    return cached

            # Fetch payment/order status from Razorpay adapter
            ref = external_reference or tx.razorpay_order_id or tx.transaction_id
            status_res = self.adapter.fetch_payment_status(ref)

            if status_res.provider_status == PaymentResultState.SUCCESS:
                # Resolve EXECUTING → SUCCESS → COMMITTED
                success_tx = transition_transaction(
                    tx,
                    TransactionState.SUCCESS,
                    razorpay_order_id=ref,
                )
                committed_tx = transition_transaction(
                    success_tx,
                    TransactionState.COMMITTED,
                )
                self._transactions[transaction_id] = committed_tx

                res = ExecutionResult(
                    success=True,
                    transaction_id=transaction_id,
                    state=TransactionState.COMMITTED,
                    external_reference=ref,
                    safe_message="Payment status successfully reconciled to SUCCESS.",
                    provider_status=PaymentResultState.SUCCESS,
                    executed_at=_utc_now(),
                )
                self._results[transaction_id] = res
                return res

            elif status_res.provider_status in (
                PaymentResultState.FAILED,
                PaymentResultState.EXPIRED,
            ):
                # Resolve EXECUTING → FAILURE → ROLLED_BACK
                failure_tx = transition_transaction(
                    tx,
                    TransactionState.FAILURE,
                )
                rolled_back_tx = transition_transaction(
                    failure_tx,
                    TransactionState.ROLLED_BACK,
                )
                self._transactions[transaction_id] = rolled_back_tx

                res = ExecutionResult(
                    success=False,
                    transaction_id=transaction_id,
                    state=TransactionState.ROLLED_BACK,
                    external_reference=ref,
                    failure_code=RejectionReason.METHOD_NOT_AUTHORIZED,
                    failure_category=ExecutionFailureCategory.PROVIDER_REJECTED,
                    safe_message="Payment status successfully reconciled to FAILED.",
                    provider_status=PaymentResultState.FAILED,
                    executed_at=_utc_now(),
                )
                self._results[transaction_id] = res
                return res

            else:
                # Remains UNKNOWN / PENDING — stay in EXECUTING state
                res = ExecutionResult(
                    success=False,
                    transaction_id=transaction_id,
                    state=TransactionState.EXECUTING,
                    external_reference=ref,
                    failure_code=RejectionReason.AUTHORIZATION_EXPIRED,
                    failure_category=ExecutionFailureCategory.TIMEOUT,
                    safe_message=(
                        "Payment status reconciliation returned UNKNOWN. "
                        "Transaction remains in EXECUTING state."
                    ),
                    provider_status=PaymentResultState.UNKNOWN,
                    executed_at=_utc_now(),
                )
                self._results[transaction_id] = res
                return res

    def _verify_pre_execution_auth(
        self,
        authorization_result: AuthorizationResult,
        transaction: Transaction,
    ) -> ExecutionResult | None:
        """Verify pre-execution authorization gate and required controls."""
        if authorization_result.decision != PolicyDecision.ALLOW:
            reason = authorization_result.rejection_reason or RejectionReason.METHOD_NOT_AUTHORIZED
            return self._reject_execution(
                transaction=transaction,
                reason=reason,
                category=ExecutionFailureCategory.AUTHORIZATION_FAILED,
                message=f"Execution blocked: Authorization decision is {authorization_result.decision.value}.",
            )

        control_outcomes = {c.control_name: c for c in authorization_result.control_outcomes}
        required_controls = [
            "MANDATE_EVALUATION",
            "MERCHANT_POLICY",
            "CART_INTEGRITY",
            "BUDGET_RESERVATION",
            "REPLAY_PROTECTION",
            "NONCE_VALIDATION",
        ]
        for ctrl_name in required_controls:
            if (
                ctrl_name not in control_outcomes
                or control_outcomes[ctrl_name].decision != PolicyDecision.ALLOW
            ):
                return self._reject_execution(
                    transaction=transaction,
                    reason=RejectionReason.CONTROL_RESULT_MISSING,
                    category=ExecutionFailureCategory.AUTHORIZATION_FAILED,
                    message=f"Execution blocked: Security control {ctrl_name} not satisfied.",
                )

        if "STEP_UP_AUTHORIZATION" in control_outcomes:
            if control_outcomes["STEP_UP_AUTHORIZATION"].decision != PolicyDecision.ALLOW:
                return self._reject_execution(
                    transaction=transaction,
                    reason=RejectionReason.STEP_UP_CONFIRMATION_INVALID,
                    category=ExecutionFailureCategory.AUTHORIZATION_FAILED,
                    message="Execution blocked: Step-up authorization required but not approved.",
                )

        return None

    def _verify_context_and_operation(
        self,
        proposal: PaymentExecuteProposalRequest,
        transaction: Transaction,
    ) -> ExecutionResult | None:
        """Verify context fields integrity between proposal and transaction."""
        if proposal.transaction_id != transaction.transaction_id:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.INVALID_TRANSACTION_STATE,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message="Transaction ID mismatch between proposal and authorized transaction.",
            )

        if proposal.merchant_id != transaction.merchant_id:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.MERCHANT_MISMATCH,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message="Merchant ID mismatch between proposal and authorized transaction.",
            )

        if proposal.buyer_id != transaction.buyer_id:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.MANDATE_NOT_IN_SCOPE,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message="Buyer ID mismatch between proposal and authorized transaction.",
            )

        if proposal.mandate_id != transaction.mandate_id:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.MANDATE_NOT_IN_SCOPE,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message="Mandate ID mismatch between proposal and authorized transaction.",
            )

        if proposal.amount_paise != transaction.amount_paise:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.INVALID_AMOUNT,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message=(
                    f"Amount mismatch: proposed ₹{proposal.amount_paise/100:.2f} "
                    f"!= authorized ₹{transaction.amount_paise/100:.2f}."
                ),
            )

        if proposal.currency != transaction.currency:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.CURRENCY_MISMATCH,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message=(
                    f"Currency mismatch: proposed {proposal.currency.value} "
                    f"!= authorized {transaction.currency.value}."
                ),
            )

        if (
            transaction.cart_hash
            and proposal.cart_hash.strip().lower() != transaction.cart_hash.strip().lower()
        ):
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.CART_INTEGRITY_VIOLATION,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message="Cart hash mismatch between proposal and authorized transaction.",
            )

        if proposal.operation.is_blocked_by_default:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.OPERATION_NOT_ALLOWED,
                category=ExecutionFailureCategory.VALIDATION_ERROR,
                message=f"Operation {proposal.operation.value} is dangerous and blocked by default.",
            )

        allowed_ops = {
            McpOperation.CREATE_ORDER,
            McpOperation.CREATE_PAYMENT_LINK,
            McpOperation.FETCH_PAYMENT,
        }
        if proposal.operation not in allowed_ops:
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.OPERATION_NOT_ALLOWED,
                category=ExecutionFailureCategory.VALIDATION_ERROR,
                message=f"Operation {proposal.operation.value} not allowed.",
            )

        return None

    def _reject_execution(
        self,
        transaction: Transaction,
        reason: RejectionReason,
        category: ExecutionFailureCategory,
        message: str,
    ) -> ExecutionResult:
        """Helper to safely reject execution pre-condition failures fail-closed."""
        if transaction.state is not TransactionState.REJECTED:
            try:
                rejected_tx = transition_transaction(
                    transaction,
                    TransactionState.REJECTED,
                    rejection_reason=reason,
                    rejection_detail=message,
                )
                self._transactions[transaction.transaction_id] = rejected_tx
            except Exception:
                pass

        res = ExecutionResult(
            success=False,
            transaction_id=transaction.transaction_id,
            state=TransactionState.REJECTED,
            failure_code=reason,
            failure_category=category,
            safe_message=message,
            provider_status=PaymentResultState.FAILED,
        )
        self._results[transaction.transaction_id] = res
        return res

    # -----------------------------------------------------------------------
    # Async Persistent Methods (S05.4 Domain Engine Persistence Integration)
    # -----------------------------------------------------------------------

    async def async_execute_payment(
        self,
        uow: AsyncUnitOfWork,
        proposal: PaymentExecuteProposalRequest,
        authorization_result: AuthorizationResult,
        transaction: Transaction,
    ) -> ExecutionResult:
        """
        Execute payment with database persistence via uow.
        Enforces 3-step boundary model:
          1. Transition state to EXECUTING in database.
          2. Invoke adapter OUTSIDE long database transaction locks.
          3. Finalize state transition to COMMITTED / ROLLED_BACK in database.
        """
        tx_id = transaction.transaction_id
        db_tx = await uow.transactions.get_transaction(tx_id)

        if db_tx is not None and db_tx.state in (
            TransactionState.COMMITTED.value,
            TransactionState.SUCCESS.value,
        ):
            return ExecutionResult(
                success=True,
                transaction_id=tx_id,
                state=TransactionState.COMMITTED,
                external_reference=db_tx.provider_payment_id or f"pay_{tx_id[:8]}",
                safe_message="Payment previously executed successfully.",
                idempotent_replay=True,
                provider_status=PaymentResultState.SUCCESS,
            )

        auth_rej = self._verify_pre_execution_auth(authorization_result, transaction)
        if auth_rej:
            await uow.transactions.transition_transaction_state(tx_id, TransactionState.REJECTED)
            return auth_rej

        ctx_rej = self._verify_context_and_operation(proposal, transaction)
        if ctx_rej:
            await uow.transactions.transition_transaction_state(tx_id, TransactionState.REJECTED)
            return ctx_rej

        if not transaction.is_executable():
            return self._reject_execution(
                transaction=transaction,
                reason=RejectionReason.INVALID_TRANSACTION_STATE,
                category=ExecutionFailureCategory.INVALID_CONTEXT,
                message=f"Transaction in state {transaction.state.value} cannot be executed.",
            )

        # Step 1: Claim EXECUTING state in DB
        _ = await uow.transactions.mark_provider_dispatch_started(tx_id)
        await uow.flush()

        trusted_request = TrustedExecutionRequest(
            transaction_id=tx_id,
            merchant_id=transaction.merchant_id,
            buyer_id=transaction.buyer_id,
            mandate_id=transaction.mandate_id,
            amount_paise=transaction.amount_paise,
            currency=transaction.currency,
            cart_hash=transaction.cart_hash or proposal.cart_hash,
            operation=proposal.operation,
            authorization_reference=authorization_result.decision_trace.get(
                "authorization_reference", f"auth_{tx_id[:8]}"
            ),
            idempotency_key=f"exec:{tx_id}",
        )

        # Step 2: Provider Invocation (HTTP network boundary)
        provider_result = self.adapter.execute_payment(trusted_request)

        # Step 3: Record final state in DB
        if provider_result.success:
            await uow.transactions.record_provider_outcome(
                tx_id,
                provider_status="SUCCESS",
                provider_payment_id=provider_result.external_reference,
            )
            await uow.transactions.transition_transaction_state(tx_id, TransactionState.SUCCESS)
            await uow.transactions.transition_transaction_state(tx_id, TransactionState.COMMITTED)

            final_res = ExecutionResult(
                success=True,
                transaction_id=tx_id,
                state=TransactionState.COMMITTED,
                external_reference=provider_result.external_reference,
                safe_message=provider_result.safe_message,
                provider_status=PaymentResultState.SUCCESS,
                raw_response_redacted=provider_result.raw_response_redacted,
                executed_at=provider_result.executed_at,
            )
        elif provider_result.provider_status == PaymentResultState.UNKNOWN:
            await uow.transactions.record_provider_outcome(
                tx_id,
                provider_status="UNKNOWN",
                provider_payment_id=provider_result.external_reference,
            )
            final_res = ExecutionResult(
                success=False,
                transaction_id=tx_id,
                state=TransactionState.EXECUTING,
                external_reference=provider_result.external_reference,
                failure_code=provider_result.failure_code or RejectionReason.AUTHORIZATION_EXPIRED,
                failure_category=provider_result.failure_category
                or ExecutionFailureCategory.TIMEOUT,
                safe_message=provider_result.safe_message or "Outcome UNKNOWN.",
                provider_status=PaymentResultState.UNKNOWN,
                raw_response_redacted=provider_result.raw_response_redacted,
                executed_at=provider_result.executed_at,
            )
        else:
            await uow.transactions.record_provider_outcome(
                tx_id,
                provider_status="FAILED",
                provider_payment_id=provider_result.external_reference,
            )
            await uow.transactions.transition_transaction_state(tx_id, TransactionState.FAILURE)
            await uow.transactions.transition_transaction_state(tx_id, TransactionState.ROLLED_BACK)

            final_res = ExecutionResult(
                success=False,
                transaction_id=tx_id,
                state=TransactionState.ROLLED_BACK,
                external_reference=provider_result.external_reference,
                failure_code=provider_result.failure_code or RejectionReason.METHOD_NOT_AUTHORIZED,
                failure_category=provider_result.failure_category,
                safe_message=provider_result.safe_message,
                provider_status=provider_result.provider_status or PaymentResultState.FAILED,
                raw_response_redacted=provider_result.raw_response_redacted,
                executed_at=provider_result.executed_at,
            )

        with self._lock:
            self._results[tx_id] = final_res

        return final_res
