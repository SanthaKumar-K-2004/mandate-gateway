"""
S07.4 — API Rate Limiter & Abuse Control Boundary.

Implements sliding-window rate limiting per credential identity and merchant identity
to protect API endpoints from excessive traffic and brute-force key enumeration.
"""

from __future__ import annotations

import time
from typing import Dict


class RateLimitExceededError(RuntimeError):
    """Raised when an API credential exceeds allowed request volume."""

    pass


class RateLimiter:
    """
    In-memory sliding-window rate limiter per identity key.
    """

    def __init__(self, requests_per_minute: int = 100, window_seconds: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        # Maps identity_key -> list of timestamp floats
        self._history: Dict[str, list[float]] = {}

    def is_allowed(self, identity_key: str) -> bool:
        """
        Check if request for identity_key is allowed under current rate limit.
        """
        if not identity_key:
            return True

        now = time.time()
        window_start = now - self.window_seconds

        timestamps = self._history.get(identity_key, [])
        # Filter out timestamps older than window_start
        valid_timestamps = [ts for ts in timestamps if ts > window_start]

        if len(valid_timestamps) >= self.requests_per_minute:
            self._history[identity_key] = valid_timestamps
            return False

        valid_timestamps.append(now)
        self._history[identity_key] = valid_timestamps
        return True

    def check_rate_limit(self, identity_key: str) -> None:
        """
        Enforce rate limit, raising RateLimitExceededError if limit is breached.
        """
        if not self.is_allowed(identity_key):
            raise RateLimitExceededError(
                f"Rate limit of {self.requests_per_minute} requests per {self.window_seconds}s "
                f"exceeded for key '{identity_key}'."
            )

    def reset(self) -> None:
        """Clear rate limit history."""
        self._history.clear()


# Default global rate limiter instance (100 requests per minute)
global_rate_limiter = RateLimiter(requests_per_minute=100, window_seconds=60)
