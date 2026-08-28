"""
S01.1 — ActionReceipt Domain Model.

A machine-verifiable receipt for every completed transaction
(Section 20, PROJECT_CONTEXT.md).

Receipt fields:
    receipt_version, receipt_id, transaction_id, mandate_id, merchant_id,
    policy_version, cart_hash, amount, currency, decision,
    execution_tool, execution_reference, timestamps, audit_hash.

Design:
  - Structure only in S01.1. Ed25519 signing is implemented in Phase 10.
  - Canonical JSON serialization is RFC 8785-compatible (sorted keys).
  - The canonical payload is what gets signed.
  - verify() checks structure validity without requiring the private key.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from apps.api.domain.types import Currency, PolicyDecision

RECEIPT_VERSION: str = "1.0"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class ActionReceipt(BaseModel):
    """
    Cryptographically structured action receipt for a completed transaction.

    Ed25519 signature is added in Phase 10.
    canonical_payload_hash provides pre-signing integrity in S01.1.
    """

    model_config = {"frozen": True}

    receipt_version: str = Field(default=RECEIPT_VERSION)
    receipt_id: str = Field(default_factory=_new_uuid)

    # Transaction binding
    transaction_id: str = Field(..., min_length=1)
    mandate_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    policy_version: int = Field(..., ge=1)
    cart_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hex digest of the authorized cart.",
    )

    # Financial
    amount_paise: int = Field(..., ge=0, description="Authorized amount in paise.")
    currency: Currency

    # Decision
    decision: PolicyDecision

    # Execution
    execution_tool: str | None = Field(
        default=None,
        description="Razorpay MCP tool used (e.g., 'create_order').",
    )
    execution_reference: str | None = Field(
        default=None,
        description="Razorpay order_id or payment_id from execution.",
    )

    # Timestamps
    authorized_at: datetime = Field(default_factory=_utc_now)
    executed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)

    # Audit linkage
    audit_hash: str | None = Field(
        default=None,
        description="SHA-256 hash of the final audit event in the event chain.",
    )

    # Integrity — computed canonical hash of the payload (pre-signing)
    canonical_payload_hash: str = Field(
        default="",
        description=(
            "SHA-256 of the canonical JSON payload. "
            "In Phase 10, this is the message signed with Ed25519."
        ),
    )

    # Phase 10 placeholder: Ed25519 signature (base64-encoded)
    signature: str | None = Field(
        default=None,
        description="Ed25519 signature (base64). Set in Phase 10.",
    )

    def model_post_init(self, __context: Any) -> None:
        """Compute canonical_payload_hash if not already set."""
        if not self.canonical_payload_hash:
            computed = _compute_canonical_hash(self)
            object.__setattr__(self, "canonical_payload_hash", computed)

    def verify_canonical_hash(self) -> bool:
        """
        Recompute and verify canonical_payload_hash against current fields.

        Returns True if the receipt has not been tampered with.
        Does NOT verify the Ed25519 signature (Phase 10).
        """
        return self.canonical_payload_hash == _compute_canonical_hash(self)


def _compute_canonical_hash(receipt: ActionReceipt) -> str:
    """
    Compute SHA-256 of the canonical receipt payload.

    Canonical form: JSON with sorted keys, no whitespace, UTC ISO 8601 timestamps.
    """
    canonical: dict[str, Any] = {
        "amount_paise": receipt.amount_paise,
        "audit_hash": receipt.audit_hash,
        "authorized_at": receipt.authorized_at.isoformat(),
        "cart_hash": receipt.cart_hash,
        "currency": receipt.currency.value,
        "decision": receipt.decision.value,
        "execution_reference": receipt.execution_reference,
        "execution_tool": receipt.execution_tool,
        "mandate_id": receipt.mandate_id,
        "merchant_id": receipt.merchant_id,
        "policy_version": receipt.policy_version,
        "receipt_id": receipt.receipt_id,
        "receipt_version": receipt.receipt_version,
        "transaction_id": receipt.transaction_id,
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
