"""
S01.7 — Budget Engine & Concurrency.

Deterministic, thread-safe financial budget reservation & accounting engine (Section 14, PROJECT_CONTEXT.md).

Fundamental Financial Invariant:
    spent_paise + reserved_paise + requested_paise <= daily_limit_paise

Features:
  1. Thread-safe atomic reservation, commit, and release using per-mandate synchronization locks.
  2. Integer paise precision only — zero floating point representation.
  3. Rejection of negative or zero reservation amounts.
  4. Strict state machine transition enforcement (RESERVED -> COMMITTED or RELEASED).
  5. Prevention of double-spend, double-reservation, double-commit, double-release, and stale state transitions.
  6. Direct integration with S01.5 SecurityControlOutcome.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import TYPE_CHECKING

from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.budget import BudgetInsufficientError, BudgetReservation, DailyBudget
from apps.api.domain.types import BudgetState, Currency, PolicyDecision, RejectionReason

if TYPE_CHECKING:
    from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True, slots=True)
class BudgetEvaluationResult:
    """Evaluation outcome from Budget Engine for a reservation request."""

    valid: bool
    decision: PolicyDecision
    mandate_id: str
    requested_paise: int
    available_paise: int
    reservation: BudgetReservation | None = None
    rejection_reason: RejectionReason | None = None
    rejection_detail: str | None = None
    evaluated_at: datetime = field(default_factory=_utc_now)

    @property
    def is_allowed(self) -> bool:
        return self.valid and self.decision == PolicyDecision.ALLOW

    def to_security_control_outcome(self) -> SecurityControlOutcome:
        """Convert result into a standardized S01.5 SecurityControlOutcome."""
        return SecurityControlOutcome(
            control_name="BUDGET",
            passed=self.valid,
            decision=self.decision,
            rejection_reason=self.rejection_reason,
            detail=self.rejection_detail,
        )


def assert_can_reserve(budget: DailyBudget, requested_paise: int) -> None:
    """
    Raise BudgetInsufficientError if adding *requested_paise* would exceed daily limit.

    Must be evaluated under a mandate lock for atomicity.
    """
    if requested_paise <= 0:
        raise ValueError(f"requested_paise must be positive, got {requested_paise}.")
    if budget.spent_paise + budget.reserved_paise + requested_paise > budget.daily_limit_paise:
        raise BudgetInsufficientError(
            f"Budget insufficient: requested {requested_paise} paise, "
            f"available {budget.available_paise} paise "
            f"(limit={budget.daily_limit_paise}, spent={budget.spent_paise}, reserved={budget.reserved_paise})."
        )


def reserve_budget(budget: DailyBudget, paise: int) -> DailyBudget:
    """Return a new DailyBudget with reserved_paise increased by *paise*."""
    assert_can_reserve(budget, paise)
    return budget.model_copy(
        update={
            "reserved_paise": budget.reserved_paise + paise,
            "updated_at": _utc_now(),
        }
    )


def commit_reservation(budget: DailyBudget, paise: int) -> DailyBudget:
    """Commit a reservation: move *paise* from reserved to spent."""
    if paise > budget.reserved_paise:
        raise ValueError(
            f"Cannot commit {paise} paise — only {budget.reserved_paise} paise reserved."
        )
    return budget.model_copy(
        update={
            "reserved_paise": budget.reserved_paise - paise,
            "spent_paise": budget.spent_paise + paise,
            "updated_at": _utc_now(),
        }
    )


def release_reservation(budget: DailyBudget, paise: int) -> DailyBudget:
    """Release a reservation: move *paise* from reserved back to available."""
    if paise > budget.reserved_paise:
        raise ValueError(
            f"Cannot release {paise} paise — only {budget.reserved_paise} paise reserved."
        )
    return budget.model_copy(
        update={
            "reserved_paise": budget.reserved_paise - paise,
            "updated_at": _utc_now(),
        }
    )


class BudgetEngine:
    """
    Thread-safe, deterministic financial Budget Reservation Engine.

    Guarantees linearizability and atomicity of budget operations across concurrent execution.
    """

    def __init__(self) -> None:
        self._budgets: dict[str, DailyBudget] = {}
        self._reservations: dict[str, BudgetReservation] = {}
        self._locks: dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()

    def _get_mandate_lock(self, mandate_id: str) -> threading.RLock:
        """Fetch or create a fine-grained reentrant lock for the target mandate."""
        with self._global_lock:
            if mandate_id not in self._locks:
                self._locks[mandate_id] = threading.RLock()
            return self._locks[mandate_id]

    def register_budget(
        self,
        mandate_id: str,
        daily_limit_paise: int,
        currency: Currency,
        date_utc: str | None = None,
        spent_paise: int = 0,
        reserved_paise: int = 0,
    ) -> DailyBudget:
        """Register or reset a daily budget snapshot for a mandate."""
        if daily_limit_paise < 0:
            raise ValueError(f"daily_limit_paise must be non-negative, got {daily_limit_paise}.")
        if spent_paise < 0 or reserved_paise < 0:
            raise ValueError("spent_paise and reserved_paise must be non-negative.")
        if spent_paise + reserved_paise > daily_limit_paise:
            raise ValueError("spent_paise + reserved_paise exceeds daily_limit_paise.")

        if date_utc is None:
            date_utc = _utc_now().strftime("%Y-%m-%d")

        lock = self._get_mandate_lock(mandate_id)
        with lock:
            budget = DailyBudget(
                mandate_id=mandate_id,
                currency=currency,
                date_utc=date_utc,
                daily_limit_paise=daily_limit_paise,
                spent_paise=spent_paise,
                reserved_paise=reserved_paise,
            )
            self._budgets[mandate_id] = budget
            return budget

    def get_budget(self, mandate_id: str) -> DailyBudget | None:
        """Return current DailyBudget for a mandate, or None if unregistered."""
        lock = self._get_mandate_lock(mandate_id)
        with lock:
            return self._budgets.get(mandate_id)

    def list_budgets(self) -> dict[str, DailyBudget]:
        """Return shallow copy of registered budgets dictionary."""
        with self._global_lock:
            return dict(self._budgets)

    def get_reservation(self, reservation_id: str) -> BudgetReservation | None:
        """Return BudgetReservation by ID, or None if not found."""
        with self._global_lock:
            return self._reservations.get(reservation_id)

    def reserve(
        self,
        mandate_id: str,
        transaction_id: str,
        amount_paise: int,
        currency: Currency,
        reservation_id: str | None = None,
        ttl_seconds: int = 300,
        at: datetime | None = None,
    ) -> BudgetEvaluationResult:
        """
        Atomically reserve requested_paise from mandate's available daily budget.

        Thread-safe under mandate lock.
        """
        eval_time = at if at is not None else _utc_now()

        # Reject non-positive amounts
        if amount_paise <= 0:
            return BudgetEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                mandate_id=mandate_id,
                requested_paise=amount_paise,
                available_paise=0,
                rejection_reason=RejectionReason.INVALID_AMOUNT,
                rejection_detail=f"Budget reservation amount must be positive integer paise, got {amount_paise}.",
                evaluated_at=eval_time,
            )

        lock = self._get_mandate_lock(mandate_id)
        with lock:
            budget = self._budgets.get(mandate_id)
            if budget is None:
                return BudgetEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    mandate_id=mandate_id,
                    requested_paise=amount_paise,
                    available_paise=0,
                    rejection_reason=RejectionReason.BUDGET_EXCEEDED,
                    rejection_detail=f"No budget registered for mandate {mandate_id}.",
                    evaluated_at=eval_time,
                )

            # Currency mismatch check
            if budget.currency != currency:
                return BudgetEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    mandate_id=mandate_id,
                    requested_paise=amount_paise,
                    available_paise=budget.available_paise,
                    rejection_reason=RejectionReason.BUDGET_CURRENCY_MISMATCH,
                    rejection_detail=(
                        f"Budget currency mismatch: mandate is in {budget.currency.value}, "
                        f"requested in {currency.value}."
                    ),
                    evaluated_at=eval_time,
                )

            # Check for duplicate reservation ID
            res_id = reservation_id if reservation_id else _new_uuid()
            if res_id in self._reservations:
                existing_res = self._reservations[res_id]
                return BudgetEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    mandate_id=mandate_id,
                    requested_paise=amount_paise,
                    available_paise=budget.available_paise,
                    rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                    rejection_detail=(
                        f"Duplicate reservation ID {res_id} already exists "
                        f"in state {existing_res.state.value}."
                    ),
                    evaluated_at=eval_time,
                )

            # Evaluate core financial invariant: spent + reserved + requested <= limit
            if budget.spent_paise + budget.reserved_paise + amount_paise > budget.daily_limit_paise:
                return BudgetEvaluationResult(
                    valid=False,
                    decision=PolicyDecision.REJECT,
                    mandate_id=mandate_id,
                    requested_paise=amount_paise,
                    available_paise=budget.available_paise,
                    rejection_reason=RejectionReason.BUDGET_EXCEEDED,
                    rejection_detail=(
                        f"Budget limit exceeded: requested {amount_paise} paise, "
                        f"available {budget.available_paise} paise (limit={budget.daily_limit_paise}, "
                        f"spent={budget.spent_paise}, reserved={budget.reserved_paise})."
                    ),
                    evaluated_at=eval_time,
                )

            # Perform atomic reservation mutation
            updated_budget = reserve_budget(budget, amount_paise)
            expires_at = datetime.fromtimestamp(
                eval_time.timestamp() + ttl_seconds, tz=timezone.utc
            )

            reservation = BudgetReservation(
                reservation_id=res_id,
                transaction_id=transaction_id,
                mandate_id=mandate_id,
                amount_paise=amount_paise,
                currency=currency,
                state=BudgetState.RESERVED,
                created_at=eval_time,
                expires_at=expires_at,
                updated_at=eval_time,
            )

            # Persist state atomically under lock
            self._budgets[mandate_id] = updated_budget
            with self._global_lock:
                self._reservations[res_id] = reservation

            return BudgetEvaluationResult(
                valid=True,
                decision=PolicyDecision.ALLOW,
                mandate_id=mandate_id,
                requested_paise=amount_paise,
                available_paise=updated_budget.available_paise,
                reservation=reservation,
                rejection_reason=None,
                rejection_detail=None,
                evaluated_at=eval_time,
            )

    def commit(
        self,
        mandate_id: str,
        reservation_id: str,
        at: datetime | None = None,
    ) -> BudgetReservation:
        """
        Commit a reservation: move amount_paise from reserved_paise to spent_paise.

        State transition: RESERVED -> COMMITTED.
        Illegal or duplicate transitions fail closed.
        """
        lock = self._get_mandate_lock(mandate_id)
        with lock:
            with self._global_lock:
                reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise ValueError(f"Reservation {reservation_id} not found.")
            if reservation.mandate_id != mandate_id:
                raise ValueError(
                    f"Reservation {reservation_id} belongs to mandate {reservation.mandate_id}, not {mandate_id}."
                )

            if reservation.state == BudgetState.COMMITTED:
                raise ValueError(
                    f"Double-commit error: Reservation {reservation_id} is already COMMITTED."
                )
            if reservation.state == BudgetState.RELEASED:
                raise ValueError(
                    f"Illegal state transition: Cannot commit RELEASED reservation {reservation_id}."
                )
            if reservation.state == BudgetState.EXPIRED:
                raise ValueError(
                    f"Illegal state transition: Cannot commit EXPIRED reservation {reservation_id}."
                )
            if reservation.state != BudgetState.RESERVED:
                raise ValueError(
                    f"Cannot commit reservation {reservation_id} in state {reservation.state.value}."
                )

            budget = self._budgets.get(mandate_id)
            if budget is None:
                raise ValueError(f"No budget registered for mandate {mandate_id}.")

            # Update budget and reservation
            updated_budget = commit_reservation(budget, reservation.amount_paise)
            eval_time = at if at is not None else _utc_now()
            updated_reservation = reservation.model_copy(
                update={
                    "state": BudgetState.COMMITTED,
                    "updated_at": eval_time,
                }
            )

            self._budgets[mandate_id] = updated_budget
            with self._global_lock:
                self._reservations[reservation_id] = updated_reservation

            return updated_reservation

    def release(
        self,
        mandate_id: str,
        reservation_id: str,
        at: datetime | None = None,
    ) -> BudgetReservation:
        """
        Release a reservation: return reserved_paise to available. spent_paise is UNCHANGED.

        State transition: RESERVED / EXPIRED -> RELEASED.
        Illegal or duplicate transitions fail closed.
        """
        lock = self._get_mandate_lock(mandate_id)
        with lock:
            with self._global_lock:
                reservation = self._reservations.get(reservation_id)
            if reservation is None:
                raise ValueError(f"Reservation {reservation_id} not found.")
            if reservation.mandate_id != mandate_id:
                raise ValueError(
                    f"Reservation {reservation_id} belongs to mandate {reservation.mandate_id}, not {mandate_id}."
                )

            if reservation.state == BudgetState.RELEASED:
                raise ValueError(
                    f"Double-release error: Reservation {reservation_id} is already RELEASED."
                )
            if reservation.state == BudgetState.COMMITTED:
                raise ValueError(
                    f"Illegal state transition: Cannot release COMMITTED reservation {reservation_id}."
                )
            if reservation.state not in (BudgetState.RESERVED, BudgetState.EXPIRED):
                raise ValueError(
                    f"Cannot release reservation {reservation_id} in state {reservation.state.value}."
                )

            budget = self._budgets.get(mandate_id)
            if budget is None:
                raise ValueError(f"No budget registered for mandate {mandate_id}.")

            # Update budget and reservation
            updated_budget = release_reservation(budget, reservation.amount_paise)
            eval_time = at if at is not None else _utc_now()
            updated_reservation = reservation.model_copy(
                update={
                    "state": BudgetState.RELEASED,
                    "updated_at": eval_time,
                }
            )

            self._budgets[mandate_id] = updated_budget
            with self._global_lock:
                self._reservations[reservation_id] = updated_reservation

            return updated_reservation

    # -----------------------------------------------------------------------
    # Async Persistent Methods (S05.4 Domain Engine Persistence Integration)
    # -----------------------------------------------------------------------

    async def async_reserve(
        self,
        uow: AsyncUnitOfWork,
        mandate_id: str,
        transaction_id: str,
        amount_paise: int,
        currency: Currency,
        reservation_id: str | None = None,
        ttl_seconds: int = 300,
        at: datetime | None = None,
    ) -> BudgetEvaluationResult:
        """
        Atomically evaluate and persist a budget reservation using uow.budgets.
        Row-locks MandateModel for atomic accounting under database concurrency.
        """
        eval_time = at if at is not None else _utc_now()

        if amount_paise <= 0:
            return BudgetEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                mandate_id=mandate_id,
                requested_paise=amount_paise,
                available_paise=0,
                rejection_reason=RejectionReason.INVALID_AMOUNT,
                rejection_detail=f"Budget reservation amount must be positive integer paise, got {amount_paise}.",
                evaluated_at=eval_time,
            )

        # 1. Lock mandate row for update in database
        mandate_row = await uow.budgets.lock_mandate_budget_for_update(mandate_id)
        if mandate_row is None:
            return BudgetEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                mandate_id=mandate_id,
                requested_paise=amount_paise,
                available_paise=0,
                rejection_reason=RejectionReason.BUDGET_EXCEEDED,
                rejection_detail=f"No budget registered for mandate {mandate_id}.",
                evaluated_at=eval_time,
            )

        daily_limit = mandate_row.daily_budget_paise
        mandate_currency = Currency(mandate_row.currency)

        if mandate_currency != currency:
            return BudgetEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                mandate_id=mandate_id,
                requested_paise=amount_paise,
                available_paise=0,
                rejection_reason=RejectionReason.BUDGET_CURRENCY_MISMATCH,
                rejection_detail=(
                    f"Budget currency mismatch: mandate is in {mandate_currency.value}, "
                    f"requested in {currency.value}."
                ),
                evaluated_at=eval_time,
            )

        res_id = reservation_id if reservation_id else _new_uuid()
        existing_res = await uow.budgets.get_reservation(res_id)
        if existing_res is not None:
            return BudgetEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                mandate_id=mandate_id,
                requested_paise=amount_paise,
                available_paise=0,
                rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                rejection_detail=f"Duplicate reservation ID {res_id} already exists in state {existing_res.state}.",
                evaluated_at=eval_time,
            )

        current_reserved_spent = await uow.budgets.calculate_reserved_total(mandate_id)
        available_paise = max(0, daily_limit - current_reserved_spent)

        if current_reserved_spent + amount_paise > daily_limit:
            return BudgetEvaluationResult(
                valid=False,
                decision=PolicyDecision.REJECT,
                mandate_id=mandate_id,
                requested_paise=amount_paise,
                available_paise=available_paise,
                rejection_reason=RejectionReason.BUDGET_EXCEEDED,
                rejection_detail=(
                    f"Budget limit exceeded: requested {amount_paise} paise, available {available_paise} paise "
                    f"(limit={daily_limit}, spent_and_reserved={current_reserved_spent})."
                ),
                evaluated_at=eval_time,
            )

        res_model = await uow.budgets.create_reservation(
            reservation_id=res_id,
            mandate_id=mandate_id,
            transaction_id=transaction_id,
            requested_paise=amount_paise,
            reserved_paise=amount_paise,
            state=BudgetState.RESERVED,
        )

        expires_at = datetime.fromtimestamp(eval_time.timestamp() + ttl_seconds, tz=timezone.utc)
        domain_res = BudgetReservation(
            reservation_id=res_model.reservation_id,
            transaction_id=res_model.transaction_id,
            mandate_id=res_model.mandate_id,
            amount_paise=res_model.requested_paise,
            currency=currency,
            state=BudgetState.RESERVED,
            created_at=eval_time,
            expires_at=expires_at,
            updated_at=eval_time,
        )

        self._budgets[mandate_id] = DailyBudget(
            mandate_id=mandate_id,
            currency=currency,
            date_utc=eval_time.strftime("%Y-%m-%d"),
            daily_limit_paise=daily_limit,
            spent_paise=0,
            reserved_paise=current_reserved_spent + amount_paise,
        )
        self._reservations[res_id] = domain_res

        return BudgetEvaluationResult(
            valid=True,
            decision=PolicyDecision.ALLOW,
            mandate_id=mandate_id,
            requested_paise=amount_paise,
            available_paise=available_paise - amount_paise,
            reservation=domain_res,
            evaluated_at=eval_time,
        )

    async def async_commit(
        self,
        uow: AsyncUnitOfWork,
        mandate_id: str,
        reservation_id: str,
        at: datetime | None = None,
    ) -> BudgetReservation:
        """Commit budget reservation in database via uow.budgets."""
        _ = await uow.budgets.lock_mandate_budget_for_update(mandate_id)
        res_model = await uow.budgets.get_reservation(reservation_id)
        if res_model is None:
            raise ValueError(f"Reservation {reservation_id} not found.")
        if res_model.mandate_id != mandate_id:
            raise ValueError(
                f"Reservation {reservation_id} belongs to mandate {res_model.mandate_id}, not {mandate_id}."
            )
        if res_model.state == BudgetState.COMMITTED.value:
            raise ValueError(
                f"Double-commit error: Reservation {reservation_id} is already COMMITTED."
            )
        if res_model.state == BudgetState.RELEASED.value:
            raise ValueError(
                f"Illegal state transition: Cannot commit RELEASED reservation {reservation_id}."
            )
        if res_model.state != BudgetState.RESERVED.value:
            raise ValueError(
                f"Cannot commit reservation {reservation_id} in state {res_model.state}."
            )

        updated_model = await uow.budgets.commit_reservation(reservation_id)
        eval_time = at if at is not None else _utc_now()
        domain_res = BudgetReservation(
            reservation_id=updated_model.reservation_id,
            transaction_id=updated_model.transaction_id,
            mandate_id=updated_model.mandate_id,
            amount_paise=updated_model.requested_paise,
            currency=Currency.INR,
            state=BudgetState.COMMITTED,
            created_at=updated_model.created_at,
            expires_at=datetime.fromtimestamp(eval_time.timestamp() + 300, tz=timezone.utc),
            updated_at=eval_time,
        )
        self._reservations[reservation_id] = domain_res
        return domain_res

    async def async_release(
        self,
        uow: AsyncUnitOfWork,
        mandate_id: str,
        reservation_id: str,
        at: datetime | None = None,
    ) -> BudgetReservation:
        """Release budget reservation in database via uow.budgets."""
        _ = await uow.budgets.lock_mandate_budget_for_update(mandate_id)
        res_model = await uow.budgets.get_reservation(reservation_id)
        if res_model is None:
            raise ValueError(f"Reservation {reservation_id} not found.")
        if res_model.mandate_id != mandate_id:
            raise ValueError(
                f"Reservation {reservation_id} belongs to mandate {res_model.mandate_id}, not {mandate_id}."
            )
        if res_model.state == BudgetState.RELEASED.value:
            raise ValueError(
                f"Double-release error: Reservation {reservation_id} is already RELEASED."
            )
        if res_model.state == BudgetState.COMMITTED.value:
            raise ValueError(
                f"Illegal state transition: Cannot release COMMITTED reservation {reservation_id}."
            )

        updated_model = await uow.budgets.release_reservation(reservation_id)
        eval_time = at if at is not None else _utc_now()
        domain_res = BudgetReservation(
            reservation_id=updated_model.reservation_id,
            transaction_id=updated_model.transaction_id,
            mandate_id=updated_model.mandate_id,
            amount_paise=updated_model.requested_paise,
            currency=Currency.INR,
            state=BudgetState.RELEASED,
            created_at=updated_model.created_at,
            expires_at=datetime.fromtimestamp(eval_time.timestamp() + 300, tz=timezone.utc),
            updated_at=eval_time,
        )
        self._reservations[reservation_id] = domain_res
        return domain_res
