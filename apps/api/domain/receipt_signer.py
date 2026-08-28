"""
S02.6 — Cryptographic Action Receipt Signer & Key Manager.

Generates RFC 8785-canonicalized, Ed25519-signed action receipts for completed
autonomous commerce transactions (Section 20, PROJECT_CONTEXT.md).

Cryptographic primitve: Ed25519 (RFC 8032) via standard `cryptography` library.
Signature encoding: Standard base64 string attached to ActionReceipt.signature.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from apps.api.domain.audit_errors import ReceiptSigningError
from apps.api.domain.receipt import ActionReceipt
from apps.api.domain.types import Currency, PolicyDecision


class Ed25519KeyManager:
    """
    Ed25519 Key Manager for receipt signing and verification.

    Supports generating fresh keypairs, exporting/importing private & public keys
    in raw 32-byte format, hex string format, base64 format, or PEM format.
    """

    def __init__(self, private_key: ed25519.Ed25519PrivateKey | None = None) -> None:
        if private_key is None:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            self._private_key = private_key
        self._public_key = self._private_key.public_key()

    @property
    def private_key(self) -> ed25519.Ed25519PrivateKey:
        return self._private_key

    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        return self._public_key

    @classmethod
    def generate(cls) -> Ed25519KeyManager:
        """Generate a new random Ed25519 keypair."""
        return cls(ed25519.Ed25519PrivateKey.generate())

    @classmethod
    def from_private_key_bytes(cls, private_bytes: bytes) -> Ed25519KeyManager:
        """Load KeyManager from 32 raw private key bytes."""
        try:
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
            return cls(priv_key)
        except Exception as exc:
            raise ReceiptSigningError(
                f"Failed to load Ed25519 private key from raw bytes: {exc}",
                details={"error": str(exc)},
            ) from exc

    @classmethod
    def from_private_key_hex(cls, private_hex: str) -> Ed25519KeyManager:
        """Load KeyManager from hex-encoded 32 private key bytes."""
        try:
            raw_bytes = bytes.fromhex(private_hex)
            return cls.from_private_key_bytes(raw_bytes)
        except Exception as exc:
            raise ReceiptSigningError(
                f"Failed to load Ed25519 private key from hex: {exc}",
                details={"error": str(exc)},
            ) from exc

    def get_private_key_bytes(self) -> bytes:
        """Return raw 32 bytes of the Ed25519 private key."""
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def get_private_key_hex(self) -> str:
        """Return hex representation of raw 32 private key bytes."""
        return self.get_private_key_bytes().hex()

    def get_public_key_bytes(self) -> bytes:
        """Return raw 32 bytes of the Ed25519 public key."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def get_public_key_hex(self) -> str:
        """Return hex representation of raw 32 public key bytes."""
        return self.get_public_key_bytes().hex()

    def get_public_key_base64(self) -> str:
        """Return base64 representation of raw 32 public key bytes."""
        return base64.b64encode(self.get_public_key_bytes()).decode("ascii")

    @staticmethod
    def load_public_key_bytes(public_bytes: bytes) -> ed25519.Ed25519PublicKey:
        """Load Ed25519PublicKey from raw 32 bytes."""
        try:
            return ed25519.Ed25519PublicKey.from_public_bytes(public_bytes)
        except Exception as exc:
            raise ReceiptSigningError(
                f"Invalid Ed25519 public key bytes: {exc}",
                details={"error": str(exc)},
            ) from exc

    @staticmethod
    def load_public_key_hex(public_hex: str) -> ed25519.Ed25519PublicKey:
        """Load Ed25519PublicKey from hex string."""
        try:
            raw_bytes = bytes.fromhex(public_hex)
            return Ed25519KeyManager.load_public_key_bytes(raw_bytes)
        except Exception as exc:
            raise ReceiptSigningError(
                f"Invalid Ed25519 public key hex string: {exc}",
                details={"error": str(exc)},
            ) from exc

    @staticmethod
    def load_public_key_base64(public_b64: str) -> ed25519.Ed25519PublicKey:
        """Load Ed25519PublicKey from base64 string."""
        try:
            raw_bytes = base64.b64decode(public_b64.encode("ascii"))
            return Ed25519KeyManager.load_public_key_bytes(raw_bytes)
        except Exception as exc:
            raise ReceiptSigningError(
                f"Invalid Ed25519 public key base64 string: {exc}",
                details={"error": str(exc)},
            ) from exc


class ActionReceiptSigner:
    """
    Constructs and Ed25519-signs ActionReceipt objects for completed transactions.
    """

    def __init__(self, key_manager: Ed25519KeyManager | None = None) -> None:
        self._key_manager = key_manager or Ed25519KeyManager.generate()

    @property
    def key_manager(self) -> Ed25519KeyManager:
        return self._key_manager

    def sign_receipt(
        self,
        *,
        transaction_id: str,
        mandate_id: str,
        merchant_id: str,
        policy_version: int,
        cart_hash: str,
        amount_paise: int,
        currency: Currency,
        decision: PolicyDecision,
        execution_tool: str | None = None,
        execution_reference: str | None = None,
        audit_hash: str | None = None,
        authorized_at: datetime | None = None,
        executed_at: datetime | None = None,
        receipt_id: str | None = None,
    ) -> ActionReceipt:
        """
        Create, canonicalize, and sign an ActionReceipt using Ed25519.

        Returns:
            Immutable ActionReceipt with canonical_payload_hash computed and
            Ed25519 signature attached.
        """
        now = datetime.now(tz=timezone.utc)
        auth_time = authorized_at or now

        kwargs: dict[str, Any] = {
            "transaction_id": transaction_id,
            "mandate_id": mandate_id,
            "merchant_id": merchant_id,
            "policy_version": policy_version,
            "cart_hash": cart_hash,
            "amount_paise": amount_paise,
            "currency": currency,
            "decision": decision,
            "execution_tool": execution_tool,
            "execution_reference": execution_reference,
            "audit_hash": audit_hash,
            "authorized_at": auth_time,
            "executed_at": executed_at,
            "created_at": now,
        }

        if receipt_id is not None:
            kwargs["receipt_id"] = receipt_id

        # 1. Instantiate unsigned receipt (model_post_init computes canonical_payload_hash)
        unsigned_receipt = ActionReceipt(**kwargs)

        # 2. Compute payload digest bytes to sign
        # We sign the canonical SHA-256 payload digest string (hex encoded) as bytes
        payload_hash_bytes = unsigned_receipt.canonical_payload_hash.encode("utf-8")

        # 3. Generate Ed25519 signature over payload digest
        try:
            signature_bytes = self._key_manager.private_key.sign(payload_hash_bytes)
            signature_b64 = base64.b64encode(signature_bytes).decode("ascii")
        except Exception as exc:
            raise ReceiptSigningError(
                f"Ed25519 signature generation failed: {exc}",
                details={"transaction_id": transaction_id, "error": str(exc)},
            ) from exc

        # 4. Return new immutable receipt with signature attached
        signed_kwargs = unsigned_receipt.model_dump()
        signed_kwargs["signature"] = signature_b64

        return ActionReceipt(**signed_kwargs)
