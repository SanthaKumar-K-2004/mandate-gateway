"""
Mandate Gateway — Base Commerce Connector Interface (M24)
Workstream 6 — Abstract interface for all commerce connectors.
Every connector explicitly declares its checkout capability (VERIFIED_API, CHECKOUT_HANDOFF, DISCOVERY_ONLY).
"""

from __future__ import annotations

import abc
from typing import Any

from apps.api.commerce.models import (
    CheckoutCapability,
    CommerceConnectorResult,
    ConnectorEnvironment,
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

    @property
    @abc.abstractmethod
    def environment(self) -> ConnectorEnvironment:
        """Explicit environment mode declared by connector (LIVE, SANDBOX, DEMO, DISABLED)."""
        pass

    @property
    def connector_name(self) -> str:
        """Human-readable connector name."""
        return self.connector_id

    @property
    def merchant_identity(self) -> str:
        """Merchant identity name or domain."""
        return "Unknown Merchant"

    @property
    def base_domain(self) -> str:
        """Primary base domain for connector."""
        return "unknown.domain"

    @property
    def enabled(self) -> bool:
        """Check if connector is active."""
        return self.environment != ConnectorEnvironment.DISABLED

    @property
    def health_status(self) -> str:
        """Connector operational health status."""
        return "HEALTHY"

    @property
    def supported_operations(self) -> list[str]:
        """List of supported operations."""
        ops = ["supports_domain", "revalidate_product", "prepare_checkout", "verify_order"]
        return ops

    def discover_products(self, query: str, max_price_paise: int) -> CommerceConnectorResult:
        """Discover products matching query and price limit from connector source."""
        return CommerceConnectorResult(
            self.connector_id, self.capability, "UNSUPPORTED", "Product discovery unsupported"
        )

    def get_product(self, product_id: str) -> Any:
        """Fetch individual product record from connector source."""
        return CommerceConnectorResult(
            self.connector_id, self.capability, "UNSUPPORTED", "Direct product query unsupported"
        )

    def reconcile(
        self, purchase_request_id: str, payment_transaction_id: str
    ) -> CommerceConnectorResult:
        """Perform connector-level ledger reconciliation."""
        return CommerceConnectorResult(
            self.connector_id,
            self.capability,
            "UNSUPPORTED",
            "Connector reconciliation unsupported",
        )

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
