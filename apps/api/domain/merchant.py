"""
S01.1 — Merchant & MerchantPolicy Domain Models.

Merchant:
  Represents a Razorpay merchant registered with Mandate Gateway.
  Immutable identity once created.

MerchantPolicy:
  Versioned, machine-readable AI commerce policy.
  Defines what AI buyers are permitted to do at this merchant.

Policy fields (Section 7, PROJECT_CONTEXT.md):
  merchant_id, ai_commerce_enabled, currency, allowed_categories,
  autonomous_purchase_limit, step_up_threshold, max_step_up_percent,
  allowed_regions, allowed_operations, blocked_operations,
  policy_version, expires_at.

Rules:
  - Policy is versioned. Changes do not mutate historical decisions.
  - A transaction binds to the applicable policy version.
  - Disabled AI commerce → all AI transactions are rejected.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import FrozenSet

from pydantic import BaseModel, Field, field_validator, model_validator

from apps.api.domain.types import Currency, McpOperation, Region


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Merchant(BaseModel):
    """
    Merchant identity record.

    Immutable after creation. merchant_id is the canonical identifier.
    """

    model_config = {"frozen": True}

    merchant_id: str = Field(
        default_factory=_new_uuid,
        description="Canonical merchant identifier (UUID).",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Merchant display name.")
    razorpay_account_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Razorpay account identifier (test mode).",
    )
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("merchant_id", "razorpay_account_id", "name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class MerchantPolicy(BaseModel):
    """
    Versioned AI commerce policy for a merchant.

    One active policy per merchant at any time.
    Historical versions are never mutated.

    All monetary limits are stored in paise (integer).
    """

    model_config = {"frozen": True}

    policy_id: str = Field(default_factory=_new_uuid)
    merchant_id: str = Field(..., min_length=1)
    policy_version: int = Field(..., ge=1, description="Monotonically increasing version number.")

    # AI commerce gate — first check in policy engine
    ai_commerce_enabled: bool = Field(
        ...,
        description=(
            "Master AI commerce switch. " "False → all AI transactions are immediately rejected."
        ),
    )

    currency: Currency = Field(..., description="The currency this policy operates in.")

    # Category / scope constraints
    allowed_categories: FrozenSet[str] = Field(
        default=frozenset(),
        description="Set of product categories AI buyers may purchase.",
    )

    # Monetary limits (stored as paise)
    autonomous_purchase_limit_paise: int = Field(
        ...,
        ge=0,
        description=(
            "Maximum single autonomous transaction amount in paise. "
            "0 means no autonomous purchases permitted."
        ),
    )
    step_up_threshold_paise: int = Field(
        ...,
        ge=0,
        description=(
            "Paise amount above which step-up approval is required. "
            "Must be <= autonomous_purchase_limit_paise."
        ),
    )
    max_step_up_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "Maximum percentage over mandate_cap that triggers step-up (not hard-reject). "
            "Typically 10 (percent)."
        ),
    )

    # Geographic constraints
    allowed_regions: FrozenSet[Region] = Field(
        default=frozenset(),
        description="Allowed transaction regions.",
    )

    # MCP operation allowlist / blocklist
    allowed_operations: FrozenSet[McpOperation] = Field(
        default=frozenset(),
        description="MCP operations explicitly permitted for AI buyers.",
    )
    blocked_operations: FrozenSet[McpOperation] = Field(
        default=frozenset(),
        description=(
            "MCP operations explicitly blocked. " "Takes precedence over allowed_operations."
        ),
    )

    # Validity window
    created_at: datetime = Field(default_factory=_utc_now)
    expires_at: datetime | None = Field(
        default=None,
        description="UTC datetime after which this policy is no longer valid.",
    )

    @model_validator(mode="after")
    def _validate_thresholds(self) -> MerchantPolicy:
        if self.step_up_threshold_paise > self.autonomous_purchase_limit_paise:
            raise ValueError(
                f"step_up_threshold_paise ({self.step_up_threshold_paise}) "
                f"must be <= autonomous_purchase_limit_paise "
                f"({self.autonomous_purchase_limit_paise})."
            )
        # Blocked and allowed sets must be disjoint
        overlap = self.allowed_operations & self.blocked_operations
        if overlap:
            ops = ", ".join(op.value for op in overlap)
            raise ValueError(f"Operations appear in both allowed and blocked sets: {ops}")
        return self

    # ------------------------------------------------------------------
    # Domain queries
    # ------------------------------------------------------------------

    def is_operation_allowed(self, operation: McpOperation) -> bool:
        """
        Return True if the given MCP operation is permitted by this policy.

        Blocked operations take strict precedence over allowed operations.
        """
        if not self.ai_commerce_enabled:
            return False
        if operation in self.blocked_operations:
            return False
        return operation in self.allowed_operations

    def is_category_allowed(self, category: str) -> bool:
        """Return True if the product category is covered by this policy."""
        return category.lower() in {c.lower() for c in self.allowed_categories}

    def is_region_allowed(self, region: Region) -> bool:
        """Return True if the transaction region is permitted."""
        return region in self.allowed_regions

    def is_active(self, at: datetime | None = None) -> bool:
        """Return True if policy has not expired relative to *at* (UTC)."""
        if self.expires_at is None:
            return True
        check_time = at if at is not None else _utc_now()
        return check_time < self.expires_at
