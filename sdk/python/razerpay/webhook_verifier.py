"""
Razerpay Python SDK — Webhook Signature Verifier
"""

from __future__ import annotations

import hmac
import hashlib


class RazerpayWebhookVerifier:
    """Helper utility for verifying HMAC-SHA256 signatures on incoming Razerpay webhooks."""

    @staticmethod
    def verify_signature(
        raw_payload: bytes | str,
        signature: str,
        secret: str,
    ) -> bool:
        """
        Verifies that an incoming webhook signature matches the payload digest.

        :param raw_payload: Raw HTTP request body (bytes or UTF-8 str).
        :param signature: Value of X-Razorpay-Signature or X-Razerpay-Webhook-Signature.
        :param secret: Shared webhook secret key.
        :return: True if valid signature, False otherwise.
        """
        if not signature or not secret:
            return False

        if isinstance(raw_payload, str):
            raw_bytes = raw_payload.encode("utf-8")
        else:
            raw_bytes = raw_payload

        expected_sig = hmac.new(
            secret.encode("utf-8"),
            raw_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig.lower(), signature.lower())
