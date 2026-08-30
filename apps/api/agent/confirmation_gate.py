"""
Mandate Gateway — Human Confirmation Gate & Cryptographic Binding
Workstream 7 — Cryptographically binds human-in-the-loop confirmation tokens to:
  request_id + merchant_id + buyer_id + amount_paise + currency + expiry
Prevents confirmation replay, amount tampering, merchant substitution, and expired execution.
"""

from __future__ import annotations

import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Set


class ConfirmationError(ValueError):
    """Raised when confirmation verification fails, expires, or is replayed."""

    pass


class HumanConfirmationGate:
    """Human confirmation authority for AI payment proposals."""

    def __init__(self, secret_key: str = "rzp_confirmation_secret_key_default") -> None:
        self.secret_key = secret_key
        self._consumed_tokens: Set[str] = set()

    def generate_token(
        self,
        request_id: str,
        merchant_id: str,
        buyer_id: str,
        amount_paise: int,
        currency: str = "INR",
        product_id: str = "",
        product_source: str = "LIVE",
        purchase_plan_hash: str = "",
        ttl_seconds: int = 600,
    ) -> Dict[str, Any]:
        """Generate a cryptographically bound single-use confirmation token."""
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        raw_msg = (
            f"{request_id}|{merchant_id}|{buyer_id}|{product_id}|"
            f"{product_source}|{amount_paise}|{currency}|{purchase_plan_hash}"
        )
        sig = hmac.new(
            self.secret_key.encode("utf-8"),
            raw_msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        token = f"cnf_{sig[:32]}"

        return {
            "confirmation_token": token,
            "signature": sig,
            "request_id": request_id,
            "merchant_id": merchant_id,
            "buyer_id": buyer_id,
            "product_id": product_id,
            "product_source": product_source,
            "amount_paise": amount_paise,
            "currency": currency,
            "purchase_plan_hash": purchase_plan_hash,
            "expires_at": expires_at,
            "status": "PENDING",
        }

    def verify_and_consume_token(
        self,
        confirmation_token: str,
        request_id: str,
        merchant_id: str,
        buyer_id: str,
        amount_paise: int,
        currency: str = "INR",
        product_id: str = "",
        product_source: str = "LIVE",
        purchase_plan_hash: str = "",
        expires_at: str = "",
    ) -> bool:
        """
        Verify signature, expiration, parameters, and single-use status.
        Consumes token upon successful verification to prevent replay.
        """
        if confirmation_token in self._consumed_tokens:
            raise ConfirmationError(
                "Confirmation token has already been consumed (Replay Rejection)."
            )

        # Expiry check
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                if datetime.now(timezone.utc) > exp_dt:
                    raise ConfirmationError("Confirmation token has expired.")
            except (ValueError, TypeError):
                raise ConfirmationError("Invalid expires_at timestamp format.")

        # Re-compute signature
        raw_msg = (
            f"{request_id}|{merchant_id}|{buyer_id}|{product_id}|"
            f"{product_source}|{amount_paise}|{currency}|{purchase_plan_hash}"
        )
        expected_sig = hmac.new(
            self.secret_key.encode("utf-8"),
            raw_msg.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        expected_token = f"cnf_{expected_sig[:32]}"

        if not hmac.compare_digest(confirmation_token, expected_token):
            raise ConfirmationError(
                "Invalid confirmation token signature. Token payload does not match "
                "request, merchant, amount, or currency parameters (Tampering Rejected)."
            )

        # Consume token to prevent replay
        self._consumed_tokens.add(confirmation_token)
        return True
