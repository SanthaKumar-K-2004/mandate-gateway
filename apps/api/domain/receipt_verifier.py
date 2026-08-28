"""
S02.6 — Offline Cryptographic Action Receipt Verifier.

Provides 5-point standalone verification of ActionReceipt objects without
requiring database access or live network connections (Section 20, PROJECT_CONTEXT.md).

Verification domains:
  1. Structural & Field Completeness: receipt_id, transaction_id, cart_hash, amount_paise.
  2. Canonical Payload Integrity: SHA-256 match over RFC 8785 canonical JSON bytes.
  3. Ed25519 Signature Validity: Cryptographic verification against public key.
  4. Context Binding Matching: Mandate, transaction, merchant, cart, and amount binding.
  5. Audit Hash Linkage: Optional verification against AuditLedger event chain digest.
"""

from __future__ import annotations

import base64
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from apps.api.contracts.audit import ReceiptVerifyResponse
from apps.api.domain.audit_ledger import AuditLedger
from apps.api.domain.receipt import ActionReceipt, _compute_canonical_hash
from apps.api.domain.receipt_signer import Ed25519KeyManager
from apps.api.domain.types import Currency, PolicyDecision


class VerificationResult:
    """Detailed verification report containing verification domain statuses."""

    def __init__(
        self,
        receipt_id: str,
        is_valid: bool,
        canonical_payload_valid: bool,
        signature_valid: bool,
        structure_valid: bool,
        binding_valid: bool,
        audit_link_valid: bool | None = None,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.receipt_id = receipt_id
        self.is_valid = is_valid
        self.canonical_payload_valid = canonical_payload_valid
        self.signature_valid = signature_valid
        self.structure_valid = structure_valid
        self.binding_valid = binding_valid
        self.audit_link_valid = audit_link_valid
        self.error = error
        self.details = details or {}

    def to_contract_response(self) -> ReceiptVerifyResponse:
        """Convert result to standard ReceiptVerifyResponse DTO."""
        return ReceiptVerifyResponse(
            receipt_id=self.receipt_id,
            is_valid=self.is_valid,
            canonical_payload_valid=self.canonical_payload_valid,
            signature_valid=self.signature_valid,
            error=self.error,
        )

    def summary(self) -> str:
        """Format human-readable verification summary for CLI and logs."""
        if self.is_valid:
            lines = [
                "VALID RECEIPT",
                "✓ Signature valid",
                "✓ Payload canonical",
                "✓ Hash valid",
                "✓ Transaction binding valid",
            ]
            if self.audit_link_valid is not None:
                lines.append("✓ Audit linkage valid")
            return "\n".join(lines)
        else:
            return (
                f"INVALID RECEIPT\n"
                f"✗ Verification failed: {self.error}\n"
                f"Payload Canonical: {self.canonical_payload_valid}\n"
                f"Signature Valid: {self.signature_valid}\n"
                f"Structure Valid: {self.structure_valid}\n"
                f"Binding Valid: {self.binding_valid}"
            )


def _load_public_key_obj(
    public_key: ed25519.Ed25519PublicKey | str | bytes,
) -> ed25519.Ed25519PublicKey:
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        return public_key
    elif isinstance(public_key, bytes):
        return Ed25519KeyManager.load_public_key_bytes(public_key)
    elif isinstance(public_key, str):
        if len(public_key) == 64 and all(c in "0123456789abcdefABCDEF" for c in public_key):
            return Ed25519KeyManager.load_public_key_hex(public_key)
        else:
            return Ed25519KeyManager.load_public_key_base64(public_key)
    else:
        raise ValueError(f"Unsupported public key type: {type(public_key)}")


def _verify_bindings(
    action_receipt: ActionReceipt,
    expected_transaction_id: str | None,
    expected_mandate_id: str | None,
    expected_merchant_id: str | None,
    expected_amount_paise: int | None,
    expected_cart_hash: str | None,
    expected_currency: Currency | None,
    expected_decision: PolicyDecision | None,
) -> list[str]:
    binding_errors: list[str] = []
    if (
        expected_transaction_id is not None
        and action_receipt.transaction_id != expected_transaction_id
    ):
        binding_errors.append(
            f"transaction_id '{action_receipt.transaction_id}' != expected '{expected_transaction_id}'"
        )
    if expected_mandate_id is not None and action_receipt.mandate_id != expected_mandate_id:
        binding_errors.append(
            f"mandate_id '{action_receipt.mandate_id}' != expected '{expected_mandate_id}'"
        )
    if expected_merchant_id is not None and action_receipt.merchant_id != expected_merchant_id:
        binding_errors.append(
            f"merchant_id '{action_receipt.merchant_id}' != expected '{expected_merchant_id}'"
        )
    if expected_amount_paise is not None and action_receipt.amount_paise != expected_amount_paise:
        binding_errors.append(
            f"amount_paise '{action_receipt.amount_paise}' != expected '{expected_amount_paise}'"
        )
    if expected_cart_hash is not None and action_receipt.cart_hash != expected_cart_hash:
        binding_errors.append(
            f"cart_hash '{action_receipt.cart_hash}' != expected '{expected_cart_hash}'"
        )
    if expected_currency is not None and action_receipt.currency != expected_currency:
        binding_errors.append(
            f"currency '{action_receipt.currency}' != expected '{expected_currency}'"
        )
    if expected_decision is not None and action_receipt.decision != expected_decision:
        binding_errors.append(
            f"decision '{action_receipt.decision}' != expected '{expected_decision}'"
        )
    return binding_errors


class ReceiptVerifier:
    """
    Standalone offline verifier for ActionReceipt JSON objects and DTOs.
    """

    @classmethod
    def verify(
        cls,
        receipt: ActionReceipt | dict[str, Any],
        public_key: ed25519.Ed25519PublicKey | str | bytes,
        *,
        expected_transaction_id: str | None = None,
        expected_mandate_id: str | None = None,
        expected_merchant_id: str | None = None,
        expected_amount_paise: int | None = None,
        expected_cart_hash: str | None = None,
        expected_currency: Currency | None = None,
        expected_decision: PolicyDecision | None = None,
        audit_ledger: AuditLedger | None = None,
    ) -> VerificationResult:
        """
        Perform 5-point verification of an ActionReceipt offline.
        """
        # 1. Parse & validate receipt structure
        if isinstance(receipt, dict):
            try:
                action_receipt = ActionReceipt(**receipt)
            except Exception as exc:
                return VerificationResult(
                    receipt_id=receipt.get("receipt_id", "unknown"),
                    is_valid=False,
                    canonical_payload_valid=False,
                    signature_valid=False,
                    structure_valid=False,
                    binding_valid=False,
                    error=f"Receipt structure parsing failed: {exc}",
                )
        else:
            action_receipt = receipt

        receipt_id = action_receipt.receipt_id

        if (
            not action_receipt.receipt_id
            or not action_receipt.transaction_id
            or not action_receipt.mandate_id
            or not action_receipt.merchant_id
            or len(action_receipt.cart_hash) != 64
            or action_receipt.amount_paise < 0
        ):
            return VerificationResult(
                receipt_id=receipt_id,
                is_valid=False,
                canonical_payload_valid=False,
                signature_valid=False,
                structure_valid=False,
                binding_valid=False,
                error="Receipt contains incomplete or invalid structural fields.",
            )

        # 2. Verify Canonical Payload Hash Integrity
        computed_hash = _compute_canonical_hash(action_receipt)
        if computed_hash != action_receipt.canonical_payload_hash:
            return VerificationResult(
                receipt_id=receipt_id,
                is_valid=False,
                canonical_payload_valid=False,
                signature_valid=False,
                structure_valid=True,
                binding_valid=False,
                error=(
                    f"Canonical payload hash mismatch: "
                    f"computed '{computed_hash}' != receipt '{action_receipt.canonical_payload_hash}'"
                ),
            )

        # 3. Verify Ed25519 Cryptographic Signature
        if not action_receipt.signature:
            return VerificationResult(
                receipt_id=receipt_id,
                is_valid=False,
                canonical_payload_valid=True,
                signature_valid=False,
                structure_valid=True,
                binding_valid=False,
                error="Receipt is missing required Ed25519 signature.",
            )

        try:
            key_obj = _load_public_key_obj(public_key)
        except Exception as exc:
            return VerificationResult(
                receipt_id=receipt_id,
                is_valid=False,
                canonical_payload_valid=True,
                signature_valid=False,
                structure_valid=True,
                binding_valid=False,
                error=f"Failed to load Ed25519 public key for verification: {exc}",
            )

        try:
            signature_bytes = base64.b64decode(action_receipt.signature.encode("ascii"))
            payload_hash_bytes = action_receipt.canonical_payload_hash.encode("utf-8")
            key_obj.verify(signature_bytes, payload_hash_bytes)
        except InvalidSignature:
            return VerificationResult(
                receipt_id=receipt_id,
                is_valid=False,
                canonical_payload_valid=True,
                signature_valid=False,
                structure_valid=True,
                binding_valid=False,
                error="Ed25519 signature is invalid for the receipt canonical payload.",
            )
        except Exception as exc:
            return VerificationResult(
                receipt_id=receipt_id,
                is_valid=False,
                canonical_payload_valid=True,
                signature_valid=False,
                structure_valid=True,
                binding_valid=False,
                error=f"Ed25519 signature decoding error: {exc}",
            )

        # 4. Verify Context & Parameter Bindings
        binding_errors = _verify_bindings(
            action_receipt,
            expected_transaction_id,
            expected_mandate_id,
            expected_merchant_id,
            expected_amount_paise,
            expected_cart_hash,
            expected_currency,
            expected_decision,
        )

        if binding_errors:
            return VerificationResult(
                receipt_id=receipt_id,
                is_valid=False,
                canonical_payload_valid=True,
                signature_valid=True,
                structure_valid=True,
                binding_valid=False,
                error=f"Context binding verification failed: {'; '.join(binding_errors)}",
            )

        # 5. Verify Audit Hash Linkage (optional)
        audit_link_valid: bool | None = None
        if audit_ledger is not None:
            if not action_receipt.audit_hash:
                return VerificationResult(
                    receipt_id=receipt_id,
                    is_valid=False,
                    canonical_payload_valid=True,
                    signature_valid=True,
                    structure_valid=True,
                    binding_valid=True,
                    audit_link_valid=False,
                    error="Receipt does not contain an audit_hash linkage digest.",
                )

            chain_ok, chain_err = audit_ledger.verify_chain()
            if not chain_ok:
                return VerificationResult(
                    receipt_id=receipt_id,
                    is_valid=False,
                    canonical_payload_valid=True,
                    signature_valid=True,
                    structure_valid=True,
                    binding_valid=True,
                    audit_link_valid=False,
                    error=f"Audit ledger chain is corrupted: {chain_err}",
                )

            latest_event = audit_ledger.get_latest_event_for_transaction(
                action_receipt.transaction_id
            )
            if not latest_event:
                return VerificationResult(
                    receipt_id=receipt_id,
                    is_valid=False,
                    canonical_payload_valid=True,
                    signature_valid=True,
                    structure_valid=True,
                    binding_valid=True,
                    audit_link_valid=False,
                    error=f"No audit event recorded in ledger for transaction_id '{action_receipt.transaction_id}'.",
                )

            if latest_event.event_hash != action_receipt.audit_hash:
                return VerificationResult(
                    receipt_id=receipt_id,
                    is_valid=False,
                    canonical_payload_valid=True,
                    signature_valid=True,
                    structure_valid=True,
                    binding_valid=True,
                    audit_link_valid=False,
                    error=(
                        f"Receipt audit_hash '{action_receipt.audit_hash}' does not match "
                        f"latest ledger event digest '{latest_event.event_hash}'."
                    ),
                )

            audit_link_valid = True

        return VerificationResult(
            receipt_id=receipt_id,
            is_valid=True,
            canonical_payload_valid=True,
            signature_valid=True,
            structure_valid=True,
            binding_valid=True,
            audit_link_valid=audit_link_valid,
            error=None,
        )
