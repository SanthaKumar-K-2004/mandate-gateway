"""
S07.3 — API Security Identity & Authorization Domain Engine.

Provides core domain data structures and functions for API credential authentication,
constant-time secret verification, scope enforcement, and tenant isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import secrets
from typing import Sequence
import uuid

# Salt prefix for API secret hashing
SECRET_HASH_SALT = "rzp_sec_v1_salt_9876543210_"


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """
    Server-derived authenticated identity representing a validated API request.

    Guarantees:
      1. Derived exclusively from server credential authentication, never client input.
      2. Immutable once constructed.
      3. Contains trusted merchant_id binding for multi-tenant isolation.
    """

    credential_id: str
    merchant_id: str
    scopes: set[str] = field(default_factory=set)
    authenticated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def has_scope(self, scope: str) -> bool:
        """Check if the principal possesses a specific scope or wildcard '*"."""
        if "*" in self.scopes or "admin" in self.scopes:
            return True
        return scope in self.scopes

    def has_all_scopes(self, required_scopes: Sequence[str]) -> bool:
        """Check if the principal possesses all requested scopes."""
        return all(self.has_scope(s) for s in required_scopes)


def hash_credential_secret(raw_secret: str) -> str:
    """
    Compute a secure salted SHA-256 hash of a raw API secret.

    Raw secrets are NEVER stored in plaintext.
    """
    if not raw_secret or not raw_secret.strip():
        raise ValueError("Raw secret cannot be empty.")
    salted_bytes = (SECRET_HASH_SALT + raw_secret.strip()).encode("utf-8")
    return hashlib.sha256(salted_bytes).hexdigest()


def verify_credential_secret(raw_secret: str, stored_hash: str) -> bool:
    """
    Verify a raw API secret against a stored hash using constant-time comparison.

    Prevents timing side-channel attacks on secret validation.
    """
    if not raw_secret or not stored_hash:
        return False
    computed_hash = hash_credential_secret(raw_secret)
    return hmac.compare_digest(computed_hash.encode("utf-8"), stored_hash.encode("utf-8"))


def generate_credential_key_pair(environment: str = "live") -> tuple[str, str, str, str]:
    """
    Generate a new API credential key pair.

    Returns:
        tuple of (credential_id, prefix, raw_secret, secret_hash)
        The raw_secret is returned ONCE to be displayed to the user upon key creation.
    """
    env_clean = "test" if environment.lower() == "test" else "live"
    cred_id = f"cred_{uuid.uuid4().hex[:12]}"
    entropy = secrets.token_hex(16)  # 32 hex chars
    prefix = f"rzp_{env_clean}_{entropy[:8]}"
    raw_secret = f"{prefix}_{entropy[8:]}"
    secret_hash = hash_credential_secret(raw_secret)
    return cred_id, prefix, raw_secret, secret_hash


def validate_merchant_access(principal: AuthenticatedPrincipal, target_merchant_id: str) -> None:
    """
    Enforce strict server-derived multi-tenant isolation.

    Raises PermissionError if principal.merchant_id does not match target_merchant_id.
    """
    if not target_merchant_id or not target_merchant_id.strip():
        raise ValueError("target_merchant_id cannot be empty.")

    # Allow administrative override if admin scope is present
    if "*" in principal.scopes or "admin" in principal.scopes:
        return

    if principal.merchant_id != target_merchant_id.strip():
        raise PermissionError(
            f"Cross-tenant access denied. Principal merchant '{principal.merchant_id}' "
            f"cannot access resource owned by merchant '{target_merchant_id}'."
        )


def validate_scopes(principal: AuthenticatedPrincipal, required_scopes: Sequence[str]) -> None:
    """
    Enforce scope authorization.

    Raises PermissionError if principal lacks any of the required scopes.
    """
    missing = [s for s in required_scopes if not principal.has_scope(s)]
    if missing:
        raise PermissionError(f"Scope authorization denied. Required scope(s) missing: {missing}.")
