"""
Mandate Gateway — Checkout Capability Resolver (M24)
Workstream 8 — Resolves checkout capability bounds (VERIFIED_API, CHECKOUT_HANDOFF, DISCOVERY_ONLY).
"""

from __future__ import annotations

from typing import Tuple

from apps.api.commerce.connector_registry import CommerceConnectorRegistry
from apps.api.commerce.models import (
    CheckoutCapability,
    ProductVerificationStatus,
    VerifiedProduct,
)


class CheckoutCapabilityResolver:
    """Evaluates product truth and merchant domain connectors to determine exact capability bounds."""

    def __init__(self, registry: CommerceConnectorRegistry) -> None:
        self.registry = registry

    def resolve_capability(self, product: VerifiedProduct) -> Tuple[CheckoutCapability, str]:
        """
        Determine exact capability for a verified product.
        Returns: (capability: CheckoutCapability, explanation: str)
        """
        # Rule 1: Unverified products or out-of-stock items cannot proceed to checkout
        if product.verification_status == ProductVerificationStatus.UNVERIFIED:
            return (
                CheckoutCapability.DISCOVERY_ONLY,
                "Product identity or price is unverified. Checkout is unavailable.",
            )

        if (
            product.verification_status == ProductVerificationStatus.OUT_OF_STOCK
            or not product.availability.is_in_stock
        ):
            return (
                CheckoutCapability.DISCOVERY_ONLY,
                "Product is currently out of stock. Checkout is unavailable.",
            )

        # Rule 2: Inspect connector registry for domain
        domain = product.merchant.domain
        connector = self.registry.resolve_connector(domain)
        capability = connector.capability

        if capability == CheckoutCapability.VERIFIED_API:
            explanation = (
                f"Product verified. Direct checkout API available via '{connector.connector_id}'."
            )
        elif capability == CheckoutCapability.CHECKOUT_HANDOFF:
            explanation = (
                "Product verified. Direct API checkout unavailable. "
                "Secure merchant checkout handoff available."
            )
        elif capability == CheckoutCapability.DISCOVERY_ONLY:
            explanation = (
                "Product discovery verified. Checkout handoff unavailable for target seller domain."
            )
        else:
            capability = CheckoutCapability.UNSUPPORTED
            explanation = "Unsupported merchant domain for checkout execution."

        return capability, explanation
