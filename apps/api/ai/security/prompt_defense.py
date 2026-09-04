"""
Prompt Injection Defense Engine.
Sanitizes untrusted external product metadata, reviews, and instructions to prevent prompt injection.
"""

import re
from typing import List, Tuple


class PromptDefenseEngine:
    """Detects and isolates prompt injection attacks in untrusted inputs."""

    SUSPICIOUS_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"bypass\s+(safety|security|policy|authorization)",
        r"execute\s+payment\s+without\s+(confirmation|verification)",
        r"override\s+(system|policy|rules|budget)",
        r"allow_unlimited",
        r"authorization_bypass",
        r"system\s*:\s*you\s+are",
        r"you\s+are\s+dan",
        r"do\s+anything\s+now",
        r"transfer\s+funds",
        r"sudo\s+",
        r"rm\s+-rf",
        r"eval\(",
        r"__import__",
    ]

    def inspect_input(self, text: str) -> Tuple[str, bool]:
        """
        Inspects text for prompt injection patterns.
        Returns: (sanitized_text, is_injection_detected)
        """
        if not text:
            return "", False

        text_lower = text.lower()
        is_injection = False

        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                is_injection = True
                break

        # Sanitize text by stripping potentially dangerous instructions
        sanitized = re.sub(r"[<>{}\\\\]", "", text)
        return sanitized, is_injection

    def sanitize_and_evaluate(self, text: str) -> Tuple[str, bool, List[str]]:
        """Evaluates text for threats and returns (sanitized_text, is_injection, threats)."""
        if not text:
            return "", False, []

        # Check zero-width invisible unicode
        has_unicode_injection = bool(re.search(r"[\u200B\u200C\u200D]", text))
        sanitized, is_injection = self.inspect_input(text)
        sanitized = re.sub(r"[\u200B\u200C\u200D]", "", sanitized)

        is_injection = is_injection or has_unicode_injection
        threats: List[str] = []
        if is_injection:
            threats.append("PROMPT_INJECTION_PATTERN")
        return sanitized, is_injection, threats

    def sanitize_external_content(self, raw_content: str) -> str:
        """
        Sanitizes untrusted external web pages/product reviews so they cannot override system prompt instructions.
        """
        if not raw_content:
            return ""

        # Remove control characters and potential prompt override patterns
        sanitized = re.sub(
            r"(?i)(ignore\s+previous|system\s*:|assistant\s*:)", "[REDACTED_TEXT]", raw_content
        )
        return sanitized[:2000]
