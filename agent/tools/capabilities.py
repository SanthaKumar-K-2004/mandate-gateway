"""
S02.2 — Tool Capability Taxonomy & Allowlist Policy.

Defines explicit capability categories, forbidden payment/admin capability guards,
and capability allowlist policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Set


class ToolCapability(str, Enum):
    """Authoritative capability classification for agent tools."""

    CATALOG_READ = "CATALOG_READ"
    MERCHANT_READ = "MERCHANT_READ"
    PRODUCT_READ = "PRODUCT_READ"
    CART_BUILD = "CART_BUILD"
    PRICE_CALCULATION = "PRICE_CALCULATION"
    PROPOSAL_CREATE = "PROPOSAL_CREATE"


# Strictly prohibited capabilities that MUST NEVER be registered or granted to AI agents
FORBIDDEN_CAPABILITIES: FrozenSet[str] = frozenset(
    {
        "payment.execute",
        "payment.authorize",
        "mandate.override",
        "budget.override",
        "nonce.override",
        "policy.override",
        "admin.override",
        "arbitrary.http",
        "arbitrary.python",
        "arbitrary.shell",
        "arbitrary.database",
    }
)


@dataclass(frozen=True, slots=True)
class CapabilityPolicy:
    """
    Capability allowlist policy defining authorized capabilities for an agent session.

    Default = DENY (empty allowlist).
    """

    allowed_capabilities: Set[ToolCapability] = field(default_factory=set)

    def is_allowed(self, capability: ToolCapability) -> bool:
        """Return True if capability is explicitly authorized in policy."""
        return capability in self.allowed_capabilities

    @classmethod
    def allow_all_safe(cls) -> CapabilityPolicy:
        """Create policy allowing all standard safe AI commerce capabilities."""
        return cls(allowed_capabilities=set(ToolCapability))
