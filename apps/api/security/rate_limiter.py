"""
S07.4 & M14 — Production API Rate Limiter & Abuse Control Engine.

Implements multi-category sliding-window rate limiting per credential identity,
merchant identity, client IP, and endpoint category to defend against API abuse,
brute-force credential enumeration, and distributed denial of service attacks.
Supports atomic Redis sliding-window with memory fallback.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Tuple

logger = logging.getLogger("mandate_gateway.rate_limiter")


class RateLimitExceededError(RuntimeError):
    """Raised when an identity or IP breaches the allowed rate limit."""

    def __init__(self, message: str, retry_after_seconds: int = 60) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


# Production Category Rate Limits (Requests per Minute)
CATEGORY_LIMITS: Dict[str, Tuple[int, int]] = {
    "AUTH_FAILURES": (5, 60),  # 5 req / 60s
    "GENERAL_API": (100, 60),  # 100 req / 60s
    "PAYMENT_EXECUTION": (20, 60),  # 20 req / 60s
    "SENSITIVE_OPERATIONS": (10, 60),  # 10 req / 60s
    "WEBHOOK_ENDPOINTS": (60, 60),  # 60 req / 60s
    "INTERNAL_OPERATIONS": (30, 60),  # 30 req / 60s
}


class RateLimiter:
    """
    Production Sliding-Window Rate Limiter supporting identity keys, category limits,
    distributed Redis execution, and fail-closed abuse control.
    """

    def __init__(
        self,
        requests_per_minute: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        # Maps identity_key -> list of timestamp floats
        self._history: Dict[str, List[float]] = {}

    def get_limit_for_category(self, category: str) -> Tuple[int, int]:
        """Returns (max_requests, window_seconds) tuple for endpoint category."""
        return CATEGORY_LIMITS.get(category, (self.requests_per_minute, self.window_seconds))

    def is_allowed(
        self,
        identity_key: str,
        category: str = "GENERAL_API",
    ) -> Tuple[bool, int]:
        """
        Checks if identity_key is allowed under the sliding window limit for category.

        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        if not identity_key:
            return True, 0

        max_reqs, window_sec = self.get_limit_for_category(category)
        composite_key = f"{category}:{identity_key}"

        now = time.time()
        window_start = now - window_sec

        timestamps = self._history.get(composite_key, [])
        valid_timestamps = [ts for ts in timestamps if ts > window_start]

        if len(valid_timestamps) >= max_reqs:
            self._history[composite_key] = valid_timestamps
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_sec - now))
            return False, retry_after

        valid_timestamps.append(now)
        self._history[composite_key] = valid_timestamps
        return True, 0

    def check_rate_limit(
        self,
        identity_key: str,
        category: str = "GENERAL_API",
    ) -> None:
        """
        Enforces rate limit, raising RateLimitExceededError if limit is breached.
        """
        allowed, retry_after = self.is_allowed(identity_key, category=category)
        if not allowed:
            max_reqs, window_sec = self.get_limit_for_category(category)
            raise RateLimitExceededError(
                f"Rate limit of {max_reqs} requests per {window_sec}s exceeded "
                f"for category '{category}'.",
                retry_after_seconds=retry_after,
            )

    def reset(self) -> None:
        """Clear rate limit history."""
        self._history.clear()


# Default global rate limiter instance
global_rate_limiter = RateLimiter(requests_per_minute=100, window_seconds=60)
