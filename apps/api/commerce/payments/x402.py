"""
S01.12 — x402-Compatible HTTP Payment Capability Layer.

Implements standard x402 HTTP 402 Payment Required parsing, payment requirement
validation, proof-of-payment token generation, replay protection, and security bounds.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from typing import Any, Dict, Optional, Set


from apps.api.commerce.payments.models import (
    PaymentProofX402,
    PaymentRequirementX402,
)


class X402PaymentError(Exception):
    """Exception raised for invalid, expired, or unsafe x402 payment requirements."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class X402PaymentAdapter:
    """
    x402 Payment Capability Adapter.

    Parses external HTTP 402 Payment Required responses and handles payment proof
    token issuance through the project's payment safety & policy core.
    """

    def __init__(self, signing_secret: str = "x402_proof_signing_secret_key_m26") -> None:
        self._secret = signing_secret.encode("utf-8")
        self._used_proofs: Set[str] = set()  # Proof token replay protection cache
        self._settled_payments: Dict[str, Dict[str, Any]] = {}

    def parse_402_header_or_body(
        self,
        resource_url: str,
        status_code: int,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
    ) -> PaymentRequirementX402:
        """
        Parses an HTTP 402 response into a structured PaymentRequirementX402 object.
        """
        if status_code != 402:
            raise X402PaymentError(
                f"HTTP status code {status_code} is not 402 Payment Required.",
                code="NOT_402_STATUS",
            )

        # Parse from body if present, else fallback to header parse
        body = body or {}

        amount_paise = body.get("amount_paise") or body.get("amount")
        if amount_paise is None and "X-Payment-Amount" in headers:
            try:
                amount_paise = int(headers["X-Payment-Amount"])
            except ValueError:
                pass

        if amount_paise is None or not isinstance(amount_paise, int) or amount_paise <= 0:
            raise X402PaymentError(
                "Missing or invalid payment amount in HTTP 402 requirement.", code="INVALID_AMOUNT"
            )

        currency = (body.get("currency") or headers.get("X-Payment-Currency") or "INR").upper()
        recipient = (
            body.get("recipient_address")
            or headers.get("X-Payment-Recipient")
            or "merchant_default_x402"
        )
        network = body.get("network") or headers.get("X-Payment-Network") or "lightning_or_razorpay"
        asset = body.get("asset") or "INR"

        ttl = body.get("ttl_seconds", 300)
        exp_time = time.time() + float(ttl)

        # Hash requirement payload to bind proof to exact parameters
        req_str = f"{resource_url}:{amount_paise}:{currency}:{recipient}:{network}:{exp_time}"
        req_hash = hashlib.sha256(req_str.encode("utf-8")).hexdigest()[:32]

        return PaymentRequirementX402(
            resource_url=resource_url,
            amount_paise=amount_paise,
            currency=currency,
            recipient_address=recipient,
            network=network,
            asset=asset,
            expiration_timestamp=exp_time,
            requirement_hash=req_hash,
            metadata=body.get("metadata", {}),
        )

    def generate_payment_proof(
        self,
        requirement: PaymentRequirementX402,
        transaction_id: str,
        agent_id: str,
    ) -> PaymentProofX402:
        """
        Generates a signed payment proof token after payment execution/authorization.
        """
        # Expiration Check
        if time.time() > requirement.expiration_timestamp:
            raise X402PaymentError(
                "x402 payment requirement has EXPIRED.", code="REQUIREMENT_EXPIRED"
            )

        raw = f"{requirement.requirement_hash}:{transaction_id}:{agent_id}:{time.time()}".encode(
            "utf-8"
        )
        sig = hmac.new(self._secret, raw, hashlib.sha256).hexdigest()[:32]
        proof_token = f"x402_proof_{uuid.uuid4().hex[:12]}_{sig}"

        proof = PaymentProofX402(
            requirement_hash=requirement.requirement_hash,
            transaction_hash=transaction_id,
            signature=sig,
            proof_token=proof_token,
            created_at=time.time(),
        )
        return proof

    def verify_and_settle_proof(
        self, proof: PaymentProofX402, requirement: PaymentRequirementX402
    ) -> bool:
        """
        Verifies proof token for replay and requirement hash binding, then settles.
        """
        # Replay Protection Check
        if proof.proof_token in self._used_proofs:
            raise X402PaymentError(
                "x402 payment proof token has already been REPLAYED/USED.", code="PROOF_REPLAYED"
            )

        # Binding Check
        if proof.requirement_hash != requirement.requirement_hash:
            raise X402PaymentError(
                "x402 payment proof requirement hash mismatch.", code="REQUIREMENT_MISMATCH"
            )

        # Mark as used (replay protection)
        self._used_proofs.add(proof.proof_token)

        self._settled_payments[proof.proof_token] = {
            "requirement": requirement,
            "proof": proof,
            "settled_at": time.time(),
            "status": "SETTLED",
        }
        return True
