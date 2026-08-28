"""
S01.1 — Audit & Receipt API Contracts.

Response schemas for:
  GET /api/transactions/{id}/events
  GET /api/receipts/{id}
  GET /api/receipts/{id}/verify
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from apps.api.domain.types import AuditEventType, Currency, PolicyDecision


class AuditEventResponse(BaseModel):
    """Response representation of an append-only audit event."""

    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    transaction_id: str | None = None
    mandate_id: str | None = None
    merchant_id: str | None = None
    buyer_id: str | None = None
    payload: dict[str, Any]
    previous_hash: str
    event_hash: str


class ReceiptResponse(BaseModel):
    """Response representation of an action receipt."""

    receipt_version: str
    receipt_id: str
    transaction_id: str
    mandate_id: str
    merchant_id: str
    policy_version: int
    cart_hash: str
    amount_paise: int
    currency: Currency
    decision: PolicyDecision
    execution_tool: str | None = None
    execution_reference: str | None = None
    authorized_at: datetime
    executed_at: datetime | None = None
    created_at: datetime
    audit_hash: str | None = None
    canonical_payload_hash: str
    signature: str | None = None


class ReceiptVerifyResponse(BaseModel):
    """Result of receipt verification check."""

    receipt_id: str
    is_valid: bool
    canonical_payload_valid: bool
    signature_valid: bool | None = None  # None until Phase 10 Ed25519 signing
    error: str | None = None
