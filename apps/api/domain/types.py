"""
S01.1 — Mandate Gateway Domain Enumerations & Value Types.

All enumerations are complete, non-overlapping, and exhaustive.
State machine transitions are NOT defined here — they live in each entity module.
This module has zero imports from the rest of the application.
"""

from __future__ import annotations

from enum import Enum, unique

# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------


@unique
class Currency(str, Enum):
    """Supported transaction currencies. INR is the primary currency."""

    INR = "INR"
    USD = "USD"


# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------


@unique
class Region(str, Enum):
    """Allowed transaction regions."""

    IN = "IN"
    US = "US"


# ---------------------------------------------------------------------------
# Mandate lifecycle
# ---------------------------------------------------------------------------


@unique
class MandateStatus(str, Enum):
    """
    Buyer mandate lifecycle states.

    Lifecycle (Section 9, PROJECT_CONTEXT.md):

        DRAFT → ACTIVE → SUSPENDED | REVOKED → EXPIRED

    Once EXPIRED, REVOKED, or SUSPENDED a mandate cannot execute.
    """

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"

    def can_execute(self) -> bool:
        """Return True only if the mandate is in an executable state."""
        return self is MandateStatus.ACTIVE

    def is_terminal(self) -> bool:
        """Return True if the mandate cannot be transitioned further."""
        return self in (MandateStatus.REVOKED, MandateStatus.EXPIRED)


# ---------------------------------------------------------------------------
# Transaction state machine
# ---------------------------------------------------------------------------


@unique
class TransactionState(str, Enum):
    """
    Transaction state machine (Section 26, PROJECT_CONTEXT.md).

    DRAFT → PROPOSED → VALIDATING
      ├──→ REJECTED
      ├──→ STEP_UP_REQUIRED → USER_APPROVED ──┐
      └─────────────────────────────────────────┘
                                               ↓
                                          RESERVED
                                               ↓
                                          AUTHORIZED
                                               ↓
                                          EXECUTING
                                         /          \\
                                    SUCCESS        FAILURE
                                       ↓              ↓
                                   COMMITTED      ROLLED_BACK
                                        \\            /
                                         ↓          ↓
                                          COMPLETED
                                               ↓
                                            RECEIPT

    Forbidden transitions (Section 26, PROJECT_CONTEXT.md):
        REJECTED    → EXECUTING
        EXPIRED     → EXECUTING
        CONSUMED    → EXECUTING
        COMPLETED   → EXECUTING
        ROLLED_BACK → COMMITTED
    """

    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    USER_APPROVED = "USER_APPROVED"
    RESERVED = "RESERVED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    COMMITTED = "COMMITTED"
    ROLLED_BACK = "ROLLED_BACK"
    COMPLETED = "COMPLETED"
    RECEIPT = "RECEIPT"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"

    # ------------------------------------------------------------------
    # Transition helpers
    # ------------------------------------------------------------------

    def legal_next_states(self) -> frozenset[TransactionState]:
        """Return the set of states legally reachable from self."""
        return _TRANSACTION_LEGAL_TRANSITIONS.get(self, frozenset())

    def can_transition_to(self, target: TransactionState) -> bool:
        """Return True if transitioning to *target* is permitted."""
        return target in self.legal_next_states()

    def is_terminal(self) -> bool:
        """Return True if no further transitions are possible."""
        return self in (
            TransactionState.REJECTED,
            TransactionState.COMPLETED,
            TransactionState.EXPIRED,
            TransactionState.RECEIPT,
        )

    def can_execute(self) -> bool:
        """Return True only if the transaction may proceed to EXECUTING."""
        return self is TransactionState.AUTHORIZED


# Legal transition graph — defined after the class to reference enum members.
_TRANSACTION_LEGAL_TRANSITIONS: dict[TransactionState, frozenset[TransactionState]] = {
    TransactionState.DRAFT: frozenset({TransactionState.PROPOSED}),
    TransactionState.PROPOSED: frozenset({TransactionState.VALIDATING}),
    TransactionState.VALIDATING: frozenset(
        {
            TransactionState.REJECTED,
            TransactionState.STEP_UP_REQUIRED,
            TransactionState.RESERVED,
        }
    ),
    TransactionState.STEP_UP_REQUIRED: frozenset({TransactionState.USER_APPROVED}),
    TransactionState.USER_APPROVED: frozenset({TransactionState.RESERVED}),
    TransactionState.RESERVED: frozenset({TransactionState.AUTHORIZED}),
    TransactionState.AUTHORIZED: frozenset({TransactionState.EXECUTING}),
    TransactionState.EXECUTING: frozenset({TransactionState.SUCCESS, TransactionState.FAILURE}),
    TransactionState.SUCCESS: frozenset({TransactionState.COMMITTED}),
    TransactionState.FAILURE: frozenset({TransactionState.ROLLED_BACK}),
    TransactionState.COMMITTED: frozenset({TransactionState.COMPLETED}),
    TransactionState.ROLLED_BACK: frozenset({TransactionState.COMPLETED}),
    TransactionState.COMPLETED: frozenset({TransactionState.RECEIPT}),
    # Terminal states — no legal outgoing transitions.
    TransactionState.REJECTED: frozenset(),
    TransactionState.RECEIPT: frozenset(),
    TransactionState.EXPIRED: frozenset(),
    TransactionState.CONSUMED: frozenset(),
}


# ---------------------------------------------------------------------------
# Policy decision
# ---------------------------------------------------------------------------


@unique
class PolicyDecision(str, Enum):
    """
    Output of the deterministic policy engine (Section 11, PROJECT_CONTEXT.md).

    Exactly three outcomes. No probabilistic authorization.
    """

    ALLOW = "ALLOW"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    REJECT = "REJECT"


# ---------------------------------------------------------------------------
# Step-up zone
# ---------------------------------------------------------------------------


@unique
class StepUpZone(str, Enum):
    """
    Step-up authorization zones (Section 16, PROJECT_CONTEXT.md).

    Zone A: cart_total <= mandate_cap              → AUTO_EXECUTE
    Zone B: mandate_cap < cart_total <= cap * 1.10 → STEP_UP_REQUIRED
    Zone C: cart_total > cap * 1.10                → HARD_REJECT
    """

    AUTO_EXECUTE = "AUTO_EXECUTE"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    HARD_REJECT = "HARD_REJECT"


# ---------------------------------------------------------------------------
# Budget reservation state machine
# ---------------------------------------------------------------------------


@unique
class BudgetState(str, Enum):
    """
    Budget reservation lifecycle (Section 14, PROJECT_CONTEXT.md).

        AVAILABLE → RESERVED → COMMITTED → SPENT
                          ↓
                       EXPIRED → RELEASED
    """

    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    COMMITTED = "COMMITTED"
    SPENT = "SPENT"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"


# ---------------------------------------------------------------------------
# Nonce lifecycle
# ---------------------------------------------------------------------------


@unique
class NonceState(str, Enum):
    """
    Single-use execution authorization nonce lifecycle (Section 15).

        ISSUED → CONSUMED
    """

    ISSUED = "ISSUED"
    CONSUMED = "CONSUMED"


# ---------------------------------------------------------------------------
# MCP operations
# ---------------------------------------------------------------------------


@unique
class McpOperation(str, Enum):
    """
    All known Razorpay MCP operations (Sections 7, 13, PROJECT_CONTEXT.md).

    Operations are split into allowed-by-default and blocked-by-default.
    The policy engine enforces per-merchant allowlist.
    """

    # Allowed shopping operations
    CREATE_ORDER = "create_order"
    CREATE_PAYMENT_LINK = "create_payment_link"
    FETCH_PAYMENT = "fetch_payment"

    # Blocked financial operations (must never be authorized for AI buyers)
    PAYOUT = "payout"
    SETTLEMENT = "settlement"
    BANK_TRANSFER = "bank_transfer"

    @property
    def is_blocked_by_default(self) -> bool:
        """Return True if this operation is dangerous and blocked by default."""
        return self in (
            McpOperation.PAYOUT,
            McpOperation.SETTLEMENT,
            McpOperation.BANK_TRANSFER,
        )


# ---------------------------------------------------------------------------
# Audit event taxonomy
# ---------------------------------------------------------------------------


@unique
class AuditEventType(str, Enum):
    """
    Security-relevant audit event types (Section 19, PROJECT_CONTEXT.md).

    All events are append-only, immutable, and hash-chained.
    """

    MANDATE_CREATED = "MANDATE_CREATED"
    MERCHANT_POLICY_CREATED = "MERCHANT_POLICY_CREATED"
    CART_PROPOSED = "CART_PROPOSED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    STEP_UP_REQUESTED = "STEP_UP_REQUESTED"
    STEP_UP_APPROVED = "STEP_UP_APPROVED"
    RESERVATION_CREATED = "RESERVATION_CREATED"
    TOOL_BLOCKED = "TOOL_BLOCKED"
    EXECUTION_AUTHORIZED = "EXECUTION_AUTHORIZED"
    PAYMENT_STARTED = "PAYMENT_STARTED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    RESERVATION_RELEASED = "RESERVATION_RELEASED"
    NONCE_REPLAY_BLOCKED = "NONCE_REPLAY_BLOCKED"
    CART_TAMPER_BLOCKED = "CART_TAMPER_BLOCKED"


# ---------------------------------------------------------------------------
# Payment result states (webhook processing)
# ---------------------------------------------------------------------------


@unique
class PaymentResultState(str, Enum):
    """
    Payment result states returned by Razorpay (Section 18, PROJECT_CONTEXT.md).

    Webhook processing must be idempotent across all states.
    """

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"

    def is_retryable(self) -> bool:
        """Return True if this result state permits a safe retry."""
        return self is PaymentResultState.UNKNOWN


# ---------------------------------------------------------------------------
# Rejection reasons — structured, machine-readable
# ---------------------------------------------------------------------------


@unique
class RejectionReason(str, Enum):
    """
    Structured rejection reason codes produced by the policy engine.

    Every REJECT decision must carry exactly one RejectionReason.
    """

    # Mandate failures
    MANDATE_EXPIRED = "MANDATE_EXPIRED"
    MANDATE_REVOKED = "MANDATE_REVOKED"
    MANDATE_NOT_ACTIVE = "MANDATE_NOT_ACTIVE"
    MANDATE_NOT_IN_SCOPE = "MANDATE_NOT_IN_SCOPE"
    MERCHANT_NOT_IN_SCOPE = "MERCHANT_NOT_IN_SCOPE"
    CATEGORY_NOT_IN_SCOPE = "CATEGORY_NOT_IN_SCOPE"
    AMOUNT_EXCEEDS_MANDATE = "AMOUNT_EXCEEDS_MANDATE"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"
    AUTONOMOUS_EXECUTION_DISABLED = "AUTONOMOUS_EXECUTION_DISABLED"
    MANDATE_TTL_EXPIRED = "MANDATE_TTL_EXPIRED"

    # Merchant policy failures
    AI_COMMERCE_DISABLED = "AI_COMMERCE_DISABLED"
    MERCHANT_CATEGORY_NOT_ALLOWED = "MERCHANT_CATEGORY_NOT_ALLOWED"
    MERCHANT_AMOUNT_LIMIT_EXCEEDED = "MERCHANT_AMOUNT_LIMIT_EXCEEDED"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    REGION_NOT_ALLOWED = "REGION_NOT_ALLOWED"
    MERCHANT_CURRENCY_NOT_SUPPORTED = "MERCHANT_CURRENCY_NOT_SUPPORTED"
    POLICY_VERSION_INVALID = "POLICY_VERSION_INVALID"
    MERCHANT_POLICY_EXPIRED = "MERCHANT_POLICY_EXPIRED"
    MERCHANT_MISMATCH = "MERCHANT_MISMATCH"

    # Cart / transaction failures
    CART_INTEGRITY_VIOLATION = "CART_INTEGRITY_VIOLATION"
    CART_TOTAL_MISMATCH = "CART_TOTAL_MISMATCH"
    CART_CURRENCY_MISMATCH = "CART_CURRENCY_MISMATCH"
    PRODUCT_UNAVAILABLE = "PRODUCT_UNAVAILABLE"

    # Security failures
    NONCE_ALREADY_CONSUMED = "NONCE_ALREADY_CONSUMED"
    AUTHORIZATION_EXPIRED = "AUTHORIZATION_EXPIRED"
    NONCE_INVALID = "NONCE_INVALID"
    INVALID_TRANSACTION_STATE = "INVALID_TRANSACTION_STATE"
    TOOL_OUTSIDE_MANDATE = "TOOL_OUTSIDE_MANDATE"
    METHOD_NOT_AUTHORIZED = "METHOD_NOT_AUTHORIZED"
    CONTROL_RESULT_MISSING = "CONTROL_RESULT_MISSING"
    REPLAY_ATTEMPT_DETECTED = "REPLAY_ATTEMPT_DETECTED"

    # Budget failures
    BUDGET_INSUFFICIENT = "BUDGET_INSUFFICIENT"
    DAILY_LIMIT_EXCEEDED = "DAILY_LIMIT_EXCEEDED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    BUDGET_CURRENCY_MISMATCH = "BUDGET_CURRENCY_MISMATCH"
    INVALID_AMOUNT = "INVALID_AMOUNT"

    # Step-up exceeded hard limit
    EXCEEDS_STEP_UP_HARD_LIMIT = "EXCEEDS_STEP_UP_HARD_LIMIT"
    STEP_UP_CONFIRMATION_INVALID = "STEP_UP_CONFIRMATION_INVALID"
    STEP_UP_CONFIRMATION_EXPIRED = "STEP_UP_CONFIRMATION_EXPIRED"
