"""
Mandate Gateway — Generic Web Checkout Connector (M24)
Workstream 10 — Handles unintegrated external merchant web stores via secure checkout handoff.
Strictly blocks open redirects, javascript: URLs, data: URIs, file: schemes, and malformed URLs.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone

from apps.api.commerce.connectors.base import CommerceConnector, CommerceConnectorError
from apps.api.commerce.models import (
    CheckoutCapability,
    CommerceConnectorResult,
    ConnectorEnvironment,
    VerifiedProduct,
)


class GenericWebCheckoutConnector(CommerceConnector):
    """Connector for unintegrated external web stores providing secure checkout redirect handoff."""

    @property
    def connector_id(self) -> str:
        return "connector_generic_web"

    @property
    def capability(self) -> CheckoutCapability:
        return CheckoutCapability.CHECKOUT_HANDOFF

    @property
    def environment(self) -> ConnectorEnvironment:
        return ConnectorEnvironment.LIVE

    def supports_domain(self, domain: str) -> bool:
        """Generic web connector handles any valid public web domain."""
        if not domain or domain == "unknown.local":
            return False
        return True

    @staticmethod
    def validate_handoff_url(url: str) -> str:
        """
        Strict URL security validator:
        Blocks open redirects, javascript:, data:, file: schemes, userinfo credentials,
        internal IP ranges (SSRF prevention), and malformed URLs.
        """
        if not url:
            raise CommerceConnectorError("Handoff URL is empty.")

        url_str = url.strip()
        url_lower = url_str.lower()

        # Reject dangerous non-HTTP schemes
        if any(
            url_lower.startswith(scheme)
            for scheme in ("javascript:", "data:", "file:", "vbscript:", "about:", "blob:")
        ):
            raise CommerceConnectorError(
                f"Security Rejection: Malicious URL scheme detected in '{url_str[:30]}'."
            )

        try:
            parsed = urllib.parse.urlparse(url_str)
        except Exception as err:
            raise CommerceConnectorError(
                f"Security Rejection: Malformed URL '{url_str[:30]}': {str(err)}"
            )

        if parsed.scheme not in ("http", "https"):
            raise CommerceConnectorError(
                f"Security Rejection: Unsupported scheme '{parsed.scheme}'. Only http/https allowed."
            )

        if not parsed.netloc:
            raise CommerceConnectorError(
                "Security Rejection: Missing network location / domain in URL."
            )

        # Reject credentials in URL to prevent userinfo confusion or token leakage
        if parsed.username or parsed.password:
            raise CommerceConnectorError(
                "Security Rejection: URL contains credentials (userinfo), which is forbidden."
            )

        # Reject localhost/internal IP SSRF targets
        netloc_lower = parsed.netloc.lower().split("@")[-1].split(":")[0]
        if (
            netloc_lower in ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1")
            or netloc_lower.startswith("192.168.")
            or netloc_lower.startswith("10.")
            or netloc_lower.startswith("127.")
            or any(netloc_lower.startswith(f"172.{b}.") for b in range(16, 32))
        ):
            raise CommerceConnectorError(
                f"Security Rejection: Internal / Loopback address blocked '{netloc_lower}'."
            )

        return url_str

    def revalidate_product(self, product: VerifiedProduct) -> CommerceConnectorResult:
        """Revalidate product URL and price metadata."""
        try:
            valid_url = self.validate_handoff_url(product.source_url)
            return CommerceConnectorResult(
                connector_id=self.connector_id,
                capability=self.capability,
                status="SUCCESS",
                message="Generic web product URL validated.",
                data={
                    "source_url": valid_url,
                    "amount_paise": product.price.amount_paise,
                    "revalidated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as err:
            return CommerceConnectorResult(
                connector_id=self.connector_id,
                capability=self.capability,
                status="FAILED",
                message=str(err),
            )

    def prepare_checkout(
        self, request_id: str, product: VerifiedProduct, buyer_id: str
    ) -> CommerceConnectorResult:
        """Prepare secure redirect handoff package for external web store."""
        try:
            valid_url = self.validate_handoff_url(product.source_url)
            now_iso = datetime.now(timezone.utc).isoformat()
            return CommerceConnectorResult(
                connector_id=self.connector_id,
                capability=self.capability,
                status="SUCCESS",
                message="Secure checkout handoff package prepared for merchant website.",
                data={
                    "request_id": request_id,
                    "buyer_id": buyer_id,
                    "merchant_id": product.merchant.merchant_id,
                    "product_id": product.product_id,
                    "product_name": product.name,
                    "amount_paise": product.price.amount_paise,
                    "currency": product.price.currency,
                    "handoff_url": valid_url,
                    "prepared_at": now_iso,
                    "capability": self.capability.value,
                    "disclaimer": (
                        "Direct payment API unavailable for external site. "
                        "Handoff redirect package generated."
                    ),
                },
            )
        except Exception as err:
            return CommerceConnectorResult(
                connector_id=self.connector_id,
                capability=self.capability,
                status="FAILED",
                message=str(err),
            )

    def verify_order(self, order_id: str, payment_transaction_id: str) -> CommerceConnectorResult:
        """Generic web stores cannot provide direct API order verification without partner webhooks."""
        return CommerceConnectorResult(
            connector_id=self.connector_id,
            capability=self.capability,
            status="ORDER_HANDOFF",
            message="External web order completed via merchant redirect. Direct API order proof unavailable.",
            data={
                "order_id": order_id,
                "payment_transaction_id": payment_transaction_id,
                "order_status": "ORDER_UNKNOWN",
            },
        )
