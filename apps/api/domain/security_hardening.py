"""
S03.3 — Security Hardening & Fail-Closed Core Engine.

Implements rate limiting, secret redaction, offline receipt cryptographic verification,
and fail-closed health posture checks (Section 34 & Section 35, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

import collections
import datetime
import re
import threading
from typing import Any

from agent.security.errors import HardeningError, HardeningErrorCode
from agent.security.types import (
    RateLimitRequest,
    RateLimitResponse,
    ReceiptVerifyRequest,
    ReceiptVerifyResponse,
    SecurityPostureStatus,
)
from apps.api.domain.receipt import ActionReceipt
from apps.api.domain.receipt_signer import Ed25519KeyManager
from apps.api.domain.receipt_verifier import ReceiptVerifier
from apps.api.domain.types import Currency, PolicyDecision

SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:secret|password|private_key|token|bearer|api_key|razorpay_secret|key_secret|auth_header|cred)",
    re.IGNORECASE,
)


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str], collections.deque[float]] = collections.defaultdict(
            collections.deque
        )

    def check_rate_limit(self, req: RateLimitRequest) -> RateLimitResponse:
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        key = (req.identifier, req.action)
        cutoff = now - req.window_seconds

        with self._lock:
            history = self._requests[key]
            # Remove outdated timestamps outside sliding window
            while history and history[0] < cutoff:
                history.popleft()

            current_count = len(history)
            if current_count >= req.max_requests:
                oldest = history[0] if history else now
                retry_after = round(max(0.1, (oldest + req.window_seconds) - now), 2)
                return RateLimitResponse(
                    allowed=False,
                    identifier=req.identifier,
                    current_count=current_count,
                    max_requests=req.max_requests,
                    window_seconds=req.window_seconds,
                    retry_after_seconds=retry_after,
                )

            history.append(now)
            return RateLimitResponse(
                allowed=True,
                identifier=req.identifier,
                current_count=current_count + 1,
                max_requests=req.max_requests,
                window_seconds=req.window_seconds,
                retry_after_seconds=0.0,
            )

    def reset(self) -> None:
        """Reset rate limiter state."""
        with self._lock:
            self._requests.clear()


class SecurityHardeningEngine:
    """Master Security Hardening & Fail-Closed Auditor."""

    def __init__(self) -> None:
        self.rate_limiter = SlidingWindowRateLimiter()
        self.key_manager = Ed25519KeyManager()
        self._db_forced_down = False
        self._redis_forced_down = False

    def set_forced_persistence_failure(
        self, db_down: bool = False, redis_down: bool = False
    ) -> None:
        """Simulate database/cache degradation for fail-closed testing."""
        self._db_forced_down = db_down
        self._redis_forced_down = redis_down

    def get_posture(self) -> SecurityPostureStatus:
        db_healthy = not self._db_forced_down
        redis_healthy = not self._redis_forced_down
        mitigations: list[str] = [
            "FAIL_CLOSED_AUTHORIZATION_GATEWAY",
            "ED25519_ACTION_RECEIPT_SIGNING",
            "SLIDING_WINDOW_RATE_LIMITING",
            "ZERO_SECRET_LEAKAGE_REDACTION",
        ]
        if not db_healthy:
            mitigations.append("FAIL_CLOSED_PERSISTENCE_MODE_ACTIVE")
        if not redis_healthy:
            mitigations.append("EPHEMERAL_CACHE_DEGRADED_DB_FALLBACK_ACTIVE")

        return SecurityPostureStatus(
            fail_closed_mode_active=True,
            database_persistence_healthy=db_healthy,
            redis_cache_healthy=redis_healthy,
            rate_limiter_active=True,
            secret_redactor_active=True,
            active_threat_mitigations=mitigations,
        )

    def check_rate_limit(self, req: RateLimitRequest) -> RateLimitResponse:
        if self._db_forced_down:
            raise HardeningError(
                code=HardeningErrorCode.DATABASE_FAIL_CLOSED,
                message="Rate limiting failed closed due to database persistence failure.",
            )
        return self.rate_limiter.check_rate_limit(req)

    def redact_sensitive_data(self, data: Any) -> Any:
        """Recursively redact sensitive keys or strings."""
        if isinstance(data, dict):
            redacted: dict[str, Any] = {}
            for k, v in data.items():
                if SENSITIVE_KEY_PATTERN.search(str(k)):
                    redacted[k] = "[REDACTED]"
                else:
                    redacted[k] = self.redact_sensitive_data(v)
            return redacted
        elif isinstance(data, list):
            return [self.redact_sensitive_data(item) for item in data]
        elif isinstance(data, str):
            if "sk_live_" in data or "sk_test_" in data or "eyJ" in data:
                return "[REDACTED_SECRET_TOKEN]"
            return data
        return data

    def verify_receipt_cryptographic_offline(
        self, req: ReceiptVerifyRequest
    ) -> ReceiptVerifyResponse:
        """Perform offline cryptographic verification of an Ed25519 signed action receipt."""
        if self._db_forced_down:
            raise HardeningError(
                code=HardeningErrorCode.DATABASE_FAIL_CLOSED,
                message="Receipt verification failed closed due to database persistence failure.",
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            decision_enum = PolicyDecision(req.decision)
            currency_enum = Currency(req.currency)
        except Exception as e:
            return ReceiptVerifyResponse(
                valid=False,
                receipt_id=req.receipt_id,
                signature_valid=False,
                payload_hash_valid=False,
                audit_chain_valid=False,
                rejection_detail=f"Invalid enum conversion: {e}",
            )

        receipt = ActionReceipt(
            receipt_version="1.0",
            receipt_id=req.receipt_id,
            transaction_id=req.transaction_id,
            mandate_id=req.mandate_id,
            merchant_id=req.merchant_id,
            policy_version=req.policy_version,
            cart_hash=req.cart_hash,
            amount_paise=req.amount_paise,
            currency=currency_enum,
            decision=decision_enum,
            execution_tool=req.execution_tool,
            execution_reference=req.execution_reference,
            authorized_at=now,
            executed_at=now,
            created_at=now,
            audit_hash=req.audit_hash,
            canonical_payload_hash="computed_at_verification",
            signature=req.signature,
        )

        res = ReceiptVerifier.verify(receipt, public_key=self.key_manager.public_key)
        return ReceiptVerifyResponse(
            valid=res.is_valid,
            receipt_id=req.receipt_id,
            signature_valid=res.signature_valid,
            payload_hash_valid=res.canonical_payload_valid,
            audit_chain_valid=res.audit_link_valid if res.audit_link_valid is not None else True,
            rejection_detail=res.error,
        )
