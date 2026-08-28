"""
API contracts for S01.7 Budget Engine & Concurrency.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from apps.api.domain.types import BudgetState, Currency, PolicyDecision, RejectionReason


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class BudgetReserveRequest(BaseModel):
    """Request contract for reserving daily budget."""

    mandate_id: str = Field(
        ..., min_length=1, description="Mandate ID against which to reserve budget."
    )
    transaction_id: str = Field(
        ..., min_length=1, description="Transaction ID for this reservation."
    )
    amount_paise: int = Field(..., gt=0, description="Amount to reserve in integer paise.")
    currency: Currency = Field(..., description="Currency of the reservation request.")
    reservation_id: str | None = Field(default=None, description="Optional custom reservation ID.")
    ttl_seconds: int = Field(
        default=300, ge=1, description="Time to live for reservation in seconds."
    )


class BudgetReserveResponse(BaseModel):
    """Response contract for budget reservation attempt."""

    success: bool = Field(..., description="True if budget was reserved atomically.")
    decision: PolicyDecision = Field(..., description="ALLOW or REJECT decision.")
    reservation_id: str | None = Field(
        default=None, description="Created reservation ID if successful."
    )
    mandate_id: str = Field(..., description="Target mandate ID.")
    amount_paise: int = Field(..., description="Requested amount in paise.")
    daily_limit_paise: int = Field(..., description="Mandate daily budget limit in paise.")
    spent_paise: int = Field(..., description="Current spent paise.")
    reserved_paise: int = Field(..., description="Current reserved paise.")
    available_paise: int = Field(..., description="Remaining available paise.")
    rejection_reason: RejectionReason | None = Field(
        default=None, description="Rejection reason if rejected."
    )
    rejection_detail: str | None = Field(
        default=None, description="Detailed explanation if rejected."
    )
    evaluated_at: datetime = Field(default_factory=_utc_now)


class BudgetCommitRequest(BaseModel):
    """Request contract for committing a budget reservation."""

    mandate_id: str = Field(..., min_length=1)
    reservation_id: str = Field(..., min_length=1)


class BudgetCommitResponse(BaseModel):
    """Response contract for budget reservation commit."""

    success: bool = Field(..., description="True if commit succeeded.")
    mandate_id: str = Field(..., description="Target mandate ID.")
    reservation_id: str = Field(..., description="Committed reservation ID.")
    state: BudgetState = Field(..., description="Updated reservation state.")
    amount_paise: int = Field(..., description="Committed amount in paise.")
    spent_paise: int = Field(..., description="Updated spent paise.")
    reserved_paise: int = Field(..., description="Updated reserved paise.")
    updated_at: datetime = Field(default_factory=_utc_now)


class BudgetReleaseRequest(BaseModel):
    """Request contract for releasing a budget reservation."""

    mandate_id: str = Field(..., min_length=1)
    reservation_id: str = Field(..., min_length=1)


class BudgetReleaseResponse(BaseModel):
    """Response contract for budget reservation release."""

    success: bool = Field(..., description="True if release succeeded.")
    mandate_id: str = Field(..., description="Target mandate ID.")
    reservation_id: str = Field(..., description="Released reservation ID.")
    state: BudgetState = Field(..., description="Updated reservation state.")
    amount_paise: int = Field(..., description="Released amount in paise.")
    spent_paise: int = Field(..., description="Spent paise (unchanged).")
    reserved_paise: int = Field(..., description="Updated reserved paise.")
    updated_at: datetime = Field(default_factory=_utc_now)
