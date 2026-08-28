"""
S01.1 — DailyBudget & BudgetReservation Data Contracts.

Budget accounting snapshot & reservation record contracts (Section 14, PROJECT_CONTEXT.md).

Data contracts only — atomic reservation algorithms belong to S01.7 (budget_engine.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field, model_validator

from apps.api.domain.types import BudgetState, Currency


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class DailyBudget(BaseModel):
    """
    Immutable daily budget snapshot contract for a mandate.

    Represents accounting state at a point in time.
    Available paise = daily_limit - spent - reserved.
    """

    model_config = {"frozen": True}

    budget_id: str = Field(default_factory=_new_uuid)
    mandate_id: str = Field(..., min_length=1)
    currency: Currency
    date_utc: str = Field(
        ...,
        description="Calendar date this budget applies to (ISO 8601: YYYY-MM-DD).",
    )

    daily_limit_paise: int = Field(..., ge=0)
    spent_paise: int = Field(default=0, ge=0)
    reserved_paise: int = Field(default=0, ge=0)

    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def _validate_budget_invariant(self) -> DailyBudget:
        if self.spent_paise + self.reserved_paise > self.daily_limit_paise:
            raise ValueError(
                f"Budget invariant violated: "
                f"spent ({self.spent_paise}) + reserved ({self.reserved_paise}) "
                f"> daily_limit ({self.daily_limit_paise})."
            )
        return self

    @property
    def available_paise(self) -> int:
        """Derived available budget: limit - spent - reserved."""
        return self.daily_limit_paise - self.spent_paise - self.reserved_paise


class BudgetReservation(BaseModel):
    """Individual reservation record contract for a single transaction."""

    model_config = {"frozen": True}

    reservation_id: str = Field(default_factory=_new_uuid)
    transaction_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    amount_paise: int = Field(..., ge=0)
    currency: Currency
    state: BudgetState = Field(default=BudgetState.RESERVED)
    created_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime = Field(
        ...,
        description="UTC datetime after which this reservation is auto-released.",
    )
    updated_at: datetime = Field(default_factory=_utc_now)

    def is_expired(self, at: datetime | None = None) -> bool:
        """Return True if the reservation has expired."""
        check_time = at if at is not None else _utc_now()
        return check_time >= self.expires_at


class BudgetInsufficientError(ValueError):
    """Raised when a budget reservation cannot be created due to insufficient funds."""
