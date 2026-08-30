"""
Mandate Gateway — Base Commerce Connector Interface (M24)
Workstream 6 — Abstract interface for all commerce connectors.
Every connector explicitly declares its checkout capability (VERIFIED_API, CHECKOUT_HANDOFF, DISCOVERY_ONLY).
"""

from __future__ import annotations

import abc

from apps.api.commerce.models import (
    CheckoutCapability,
    CommerceConnectorResult,
    VerifiedProduct,
)


class CommerceConnectorError(RuntimeError):
    """Raised when commerce connector operations fail."""

    pass


class CommerceConnector(abc.ABC):
    """Abstract Base Class for Commerce Connectors."""

    @property
    @abc.abstractmethod
    def connector_id(self) -> str:
        """Unique connector identifier."""
        pass

    @property
    @abc.abstractmethod
    def capability(self) -> CheckoutCapability:
        """Explicit checkout capability declared by connector."""
        pass

    @abc.abstractmethod
    def supports_domain(self, domain: str) -> bool:
        """Check if connector supports target merchant domain."""
        pass

    @abc.abstractmethod
    def revalidate_product(self, product: VerifiedProduct) -> CommerceConnectorResult:
        """Revalidate product price and stock availability against connector source."""
        pass

    @abc.abstractmethod
    def prepare_checkout(
        self, request_id: str, product: VerifiedProduct, buyer_id: str
    ) -> CommerceConnectorResult:
        """Prepare checkout package or redirect handoff for verified product."""
        pass

    @abc.abstractmethod
    def verify_order(self, order_id: str, payment_transaction_id: str) -> CommerceConnectorResult:
        """Verify order status with authoritative evidence from merchant source."""
        pass
