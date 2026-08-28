"""
S02.3 — Commerce Prompt Injection & Catalog Poisoning Defense.

Sanitizes text inputs, scans catalog product descriptions for embedded prompt injection attacks,
and neutralizes authority key injection attempts.
"""

from __future__ import annotations

import re
from typing import Any, Set

from agent.intent.errors import IntentErrorCode, IntentValidationError

# Prompt injection attack pattern regexes
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|above|all)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s+override", re.IGNORECASE),
    re.compile(r"authorize\s+payment", re.IGNORECASE),
    re.compile(r"payout\s+to", re.IGNORECASE),
    re.compile(r"skip\s+(policy|mandate|budget|nonce|step_up)", re.IGNORECASE),
    re.compile(r"bypass\s+(auth|security|mandate)", re.IGNORECASE),
    re.compile(r"admin_override", re.IGNORECASE),
    re.compile(r"payment_approved", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+admin\s+mode", re.IGNORECASE),
]

# Authority keys strictly prohibited in untrusted input payloads
FORBIDDEN_AUTHORITY_KEYS: Set[str] = {
    "authorized",
    "approved",
    "payment_approved",
    "skip_mandate",
    "skip_policy",
    "skip_budget",
    "skip_nonce",
    "skip_step_up",
    "bypass_auth",
    "admin_override",
    "role",
    "is_admin",
    "trusted",
    "authorization_result",
    "payment_status",
}

MAX_PROMPT_TEXT_LENGTH: int = 5000


class PromptInjectionDefense:
    """
    Sanitizer and security scanner protecting the agent proposal boundary from text poisoning.
    """

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize free-text user prompt or catalog string.

        Strips control characters and truncates to maximum allowed length.
        """
        if not text:
            return ""

        # Remove control characters except newline (\n) and tab (\t)
        sanitized = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)

        # Truncate to maximum length
        if len(sanitized) > MAX_PROMPT_TEXT_LENGTH:
            sanitized = sanitized[:MAX_PROMPT_TEXT_LENGTH]

        return sanitized

    @classmethod
    def scan_catalog_poisoning(cls, item_data: dict[str, Any]) -> None:
        """
        Scan catalog product fields (name, description, category, metadata) for prompt injection.

        Raises IntentValidationError(CATALOG_POISONING_DETECTED) if attack signature is found.
        """
        search_targets = [
            str(item_data.get("name", "")),
            str(item_data.get("description", "")),
            str(item_data.get("category", "")),
            str(item_data.get("metadata", "")),
        ]

        for target in search_targets:
            if not target:
                continue
            for pattern in PROMPT_INJECTION_PATTERNS:
                if pattern.search(target):
                    raise IntentValidationError(
                        IntentErrorCode.CATALOG_POISONING_DETECTED,
                        f"Prompt injection attack signature detected in catalog item field: {target!r}.",
                    )

    @classmethod
    def scan_authority_injection(cls, payload: Any) -> None:
        """
        Recursively scan payload for forbidden authority keys.

        Raises IntentValidationError(AUTHORITY_INJECTION_ATTEMPT) if found.
        """
        if isinstance(payload, dict):
            for k, v in payload.items():
                if isinstance(k, str) and k.lower() in FORBIDDEN_AUTHORITY_KEYS:
                    raise IntentValidationError(
                        IntentErrorCode.AUTHORITY_INJECTION_ATTEMPT,
                        f"Forbidden authority claim key {k!r} detected in untrusted intent payload.",
                    )
                cls.scan_authority_injection(v)
        elif isinstance(payload, list):
            for item in payload:
                cls.scan_authority_injection(item)
