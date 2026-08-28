"""
S02.6 — Audit Ledger & Cryptographic Action Receipt Error Definitions.

Defines structured exception types and error codes for audit ledger operations,
hash chain verification, Ed25519 receipt signing, and offline receipt verification.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class AuditErrorCode(str, Enum):
    """Machine-readable error codes for audit ledger and receipt verification."""

    GENESIS_HASH_MISMATCH = "GENESIS_HASH_MISMATCH"
    CHAIN_LINKAGE_BROKEN = "CHAIN_LINKAGE_BROKEN"
    EVENT_HASH_MISMATCH = "EVENT_HASH_MISMATCH"
    EVENT_PAYLOAD_TAMPERED = "EVENT_PAYLOAD_TAMPERED"
    EVENT_OUT_OF_ORDER = "EVENT_OUT_OF_ORDER"

    INVALID_KEYPAIR = "INVALID_KEYPAIR"
    RECEIPT_SIGNING_FAILED = "RECEIPT_SIGNING_FAILED"
    RECEIPT_VERIFICATION_FAILED = "RECEIPT_VERIFICATION_FAILED"
    CANONICAL_HASH_MISMATCH = "CANONICAL_HASH_MISMATCH"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    AUDIT_LINK_MISSING = "AUDIT_LINK_MISSING"


class AuditLedgerError(Exception):
    """Base exception for audit ledger and action receipt operations."""

    def __init__(
        self,
        code: AuditErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


class AuditChainTamperedError(AuditLedgerError):
    """Raised when an audit hash chain fails integrity verification."""

    def __init__(
        self,
        message: str,
        index: int,
        expected_hash: str,
        actual_hash: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        merged_details = {
            "tampered_index": index,
            "expected_hash": expected_hash,
            "actual_hash": actual_hash,
            **(details or {}),
        }
        super().__init__(
            code=AuditErrorCode.CHAIN_LINKAGE_BROKEN,
            message=message,
            details=merged_details,
        )


class ReceiptSigningError(AuditLedgerError):
    """Raised when Ed25519 receipt signing fails."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=AuditErrorCode.RECEIPT_SIGNING_FAILED,
            message=message,
            details=details,
        )


class ReceiptVerificationError(AuditLedgerError):
    """Raised when offline receipt verification fails."""

    def __init__(
        self,
        code: AuditErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            details=details,
        )
