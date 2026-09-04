"""
S01.12 — Universal Agent Protocol (UAP) Aligned Authorization Layer.

Implements delegated authority tokens, policy constraints, revocation status management,
and fail-closed authorization checks for agentic commerce transactions.
"""

from __future__ import annotations

import hmac
import hashlib
import time
import uuid
from typing import Dict, List, Optional


from apps.api.commerce.payments.models import (
    AuthorizationPolicy,
    AuthorizationStatus,
)


class UAPAuthorizationError(Exception):
    """Exception raised when UAP authorization validation fails."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class UAPAuthorizationLayer:
    """
    UAP-Aligned Delegated Authorization Manager.

    Provides cryptographically verified, revocable, bounded delegation tokens
    enabling human users to safely delegate financial authority to AI agents.
    """

    def __init__(self, secret_key: str = "uap_delegation_secret_key_m26") -> None:
        self._secret = secret_key.encode("utf-8")
        self._authorizations: Dict[str, AuthorizationPolicy] = {}
        self._tokens: Dict[str, str] = {}  # token -> authorization_id

    def issue_authorization(
        self,
        agent_id: str,
        user_id: str,
        max_amount_paise: int = 50000,
        daily_limit_paise: int = 200000,
        scope_merchants: Optional[List[str]] = None,
        category_scope: Optional[List[str]] = None,
        ttl_seconds: float = 86400,
    ) -> AuthorizationPolicy:
        """Issue a new UAP-aligned delegated authorization token."""
        auth_id = f"uap_auth_{uuid.uuid4().hex[:12]}"
        exp_time = time.time() + ttl_seconds

        # Generate HMAC token signature
        raw_msg = f"{auth_id}:{agent_id}:{user_id}:{max_amount_paise}:{exp_time}".encode("utf-8")
        token_sig = hmac.new(self._secret, raw_msg, hashlib.sha256).hexdigest()[:32]
        token = f"uap_tok_{auth_id[-8:]}_{token_sig}"

        policy = AuthorizationPolicy(
            authorization_id=auth_id,
            agent_id=agent_id,
            user_id=user_id,
            scope_merchants=scope_merchants or [],
            max_amount_paise=max_amount_paise,
            daily_limit_paise=daily_limit_paise,
            allowed_currency="INR",
            category_scope=category_scope or ["grocery", "general", "beverage"],
            expiration_timestamp=exp_time,
            status=AuthorizationStatus.ACTIVE,
            token=token,
        )

        self._authorizations[auth_id] = policy
        self._tokens[token] = auth_id
        return policy

    def revoke_authorization(
        self, authorization_id: str, reason: str = "User revoked delegation"
    ) -> bool:
        """Immediately revoke an active authorization delegation."""
        policy = self._authorizations.get(authorization_id)
        if not policy:
            return False
        policy.status = AuthorizationStatus.REVOKED
        return True

    def suspend_authorization(self, authorization_id: str) -> bool:
        """Temporarily suspend an active authorization delegation."""
        policy = self._authorizations.get(authorization_id)
        if not policy:
            return False
        policy.status = AuthorizationStatus.SUSPENDED
        return True

    def validate_authorization(
        self,
        token_or_id: str,
        agent_id: str,
        merchant_id: str,
        category: str,
        amount_paise: int,
    ) -> AuthorizationPolicy:
        """
        Validates token or authorization ID against agent delegation rules.
        Fails closed immediately if revoked, expired, suspended, or out of scope.
        """
        auth_id = self._tokens.get(token_or_id, token_or_id)
        policy = self._authorizations.get(auth_id)

        if not policy:
            raise UAPAuthorizationError(
                "UAP delegation policy not found.", code="AUTHORIZATION_NOT_FOUND"
            )

        # 1. Status Check
        if policy.status == AuthorizationStatus.REVOKED:
            raise UAPAuthorizationError(
                "UAP delegation policy has been REVOKED.", code="AUTHORIZATION_REVOKED"
            )
        if policy.status == AuthorizationStatus.SUSPENDED:
            raise UAPAuthorizationError(
                "UAP delegation policy is currently SUSPENDED.", code="AUTHORIZATION_SUSPENDED"
            )
        if policy.status == AuthorizationStatus.CONSUMED:
            raise UAPAuthorizationError(
                "Single-use UAP authorization token already CONSUMED.",
                code="TOKEN_ALREADY_CONSUMED",
            )
        if policy.status != AuthorizationStatus.ACTIVE:
            raise UAPAuthorizationError(
                f"UAP delegation policy is in invalid status '{policy.status.value}'.",
                code="INVALID_STATUS",
            )

        # 2. Expiration Check
        if time.time() > policy.expiration_timestamp:
            policy.status = AuthorizationStatus.EXPIRED
            raise UAPAuthorizationError(
                "UAP delegation policy has EXPIRED.", code="AUTHORIZATION_EXPIRED"
            )

        # 3. Agent Binding Check
        if policy.agent_id != agent_id:
            raise UAPAuthorizationError(
                "Agent identity mismatch for UAP delegation token.", code="AGENT_MISMATCH"
            )

        # 4. Merchant Scope Check
        if policy.scope_merchants and merchant_id not in policy.scope_merchants:
            raise UAPAuthorizationError(
                f"Merchant '{merchant_id}' is outside delegated merchant scope.",
                code="MERCHANT_OUT_OF_SCOPE",
            )

        # 5. Category Scope Check
        if policy.category_scope and category.lower() not in [
            c.lower() for c in policy.category_scope
        ]:
            raise UAPAuthorizationError(
                f"Category '{category}' is outside delegated category scope.",
                code="CATEGORY_OUT_OF_SCOPE",
            )

        # 6. Max Amount Check
        if amount_paise > policy.max_amount_paise:
            max_r = policy.max_amount_paise // 100
            amt_r = amount_paise / 100
            raise UAPAuthorizationError(
                f"Requested amount ₹{amt_r:.2f} exceeds delegated max amount ₹{max_r}.",
                code="AMOUNT_EXCEEDS_DELEGATION",
            )

        return policy

    def consume_authorization(self, token_or_id: str, single_use: bool = False) -> None:
        """Mark authorization as consumed if configured as single-use."""
        auth_id = self._tokens.get(token_or_id, token_or_id)
        policy = self._authorizations.get(auth_id)
        if policy and single_use:
            policy.status = AuthorizationStatus.CONSUMED
