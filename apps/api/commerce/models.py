"""
Mandate Gateway — Commerce Domain Models (M24)
Workstream 1 — Strongly-typed domain models, enums, and data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProductVerificationStatus(str, Enum):
    """Product verification state machine values."""

    UNVERIFIED = "UNVERIFIED"
    SOURCE_BACKED = "SOURCE_BACKED"
    PRODUCT_VERIFIED = "PRODUCT_VERIFIED"
    PRICE_CHANGED = "PRICE_CHANGED"
    OUT_OF_STOCK = "OUT_OF_STOCK"


class CheckoutCapability(str, Enum):
    """Supported checkout execution capabilities."""

    VERIFIED_API = "VERIFIED_API"
    CHECKOUT_HANDOFF = "CHECKOUT_HANDOFF"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    UNSUPPORTED = "UNSUPPORTED"


class OrderStatus(str, Enum):
    """Authoritative order outcome state machine values."""

    ORDER_PENDING = "ORDER_PENDING"
    ORDER_VERIFIED = "ORDER_VERIFIED"
    ORDER_UNKNOWN = "ORDER_UNKNOWN"
    ORDER_FAILED = "ORDER_FAILED"


class ConnectorEnvironment(str, Enum):
    """Execution environment mode for commerce connectors."""

    LIVE = "LIVE"
    SANDBOX = "SANDBOX"
    DEMO = "DEMO"
    DISABLED = "DISABLED"


class ReconciliationState(str, Enum):
    """Reconciliation state machine values for commerce transactions."""

    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    PAYMENT_FOUND = "PAYMENT_FOUND"
    ORDER_FOUND = "ORDER_FOUND"
    BOTH_CONFIRMED = "BOTH_CONFIRMED"
    PAYMENT_ONLY = "PAYMENT_ONLY"
    ORDER_ONLY = "ORDER_ONLY"
    UNRESOLVED = "UNRESOLVED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass
class PriceEvidence:
    """Evidence record for a verified live product price."""

    amount_paise: int
    currency: str = "INR"
    verified_at: str = ""
    evidence_url: str = ""
    evidence_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount_paise": self.amount_paise,
            "currency": self.currency,
            "verified_at": self.verified_at,
            "evidence_url": self.evidence_url,
            "evidence_hash": self.evidence_hash,
        }


@dataclass
class AvailabilityEvidence:
    """Evidence record for live product availability."""

    is_in_stock: bool
    stock_quantity: Optional[int] = None
    verified_at: str = ""
    evidence_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_in_stock": self.is_in_stock,
            "stock_quantity": self.stock_quantity,
            "verified_at": self.verified_at,
            "evidence_url": self.evidence_url,
        }


@dataclass
class MerchantIdentity:
    """Identity record distinguishing product seller from search/payment providers."""

    merchant_id: str
    domain: str
    legal_name: str = ""
    identity_status: str = "VERIFIED"  # VERIFIED, UNKNOWN, UNTRUSTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "domain": self.domain,
            "legal_name": self.legal_name,
            "identity_status": self.identity_status,
        }


@dataclass
class VerifiedProduct:
    """Complete verified product representation."""

    product_id: str
    name: str
    description: str
    price: PriceEvidence
    availability: AvailabilityEvidence
    merchant: MerchantIdentity
    source_url: str
    retrieved_at: str
    verification_status: ProductVerificationStatus = ProductVerificationStatus.UNVERIFIED
    evidence_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "price": self.price.to_dict(),
            "availability": self.availability.to_dict(),
            "merchant": self.merchant.to_dict(),
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "verification_status": self.verification_status.value,
            "evidence_hash": self.evidence_hash,
        }


@dataclass
class ProductTruth:
    """Evaluated product truth state."""

    product: VerifiedProduct
    is_sku_verified: bool
    is_price_verified: bool
    is_merchant_verified: bool
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product": self.product.to_dict(),
            "is_sku_verified": self.is_sku_verified,
            "is_price_verified": self.is_price_verified,
            "is_merchant_verified": self.is_merchant_verified,
            "validation_errors": self.validation_errors,
        }


@dataclass
class CheckoutPreparation:
    """Prepared checkout state package prior to human confirmation."""

    preparation_id: str
    request_id: str
    merchant_id: str
    buyer_id: str
    product: VerifiedProduct
    capability: CheckoutCapability
    handoff_url: Optional[str] = None
    confirmation_token: Optional[str] = None
    expires_at: str = ""
    plan_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preparation_id": self.preparation_id,
            "request_id": self.request_id,
            "merchant_id": self.merchant_id,
            "buyer_id": self.buyer_id,
            "product": self.product.to_dict(),
            "capability": self.capability.value,
            "handoff_url": self.handoff_url,
            "confirmation_token": self.confirmation_token,
            "expires_at": self.expires_at,
            "plan_hash": self.plan_hash,
        }


@dataclass
class OrderEvidence:
    """Authoritative evidence for an executed commerce order."""

    order_id: str
    merchant_order_id: str
    payment_transaction_id: str
    amount_paise: int
    currency: str
    verification_source: str
    verified_at: str
    evidence_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "merchant_order_id": self.merchant_order_id,
            "payment_transaction_id": self.payment_transaction_id,
            "amount_paise": self.amount_paise,
            "currency": self.currency,
            "verification_source": self.verification_source,
            "verified_at": self.verified_at,
            "evidence_hash": self.evidence_hash,
        }


@dataclass
class CheckoutOutcome:
    """Authoritative outcome for a checkout attempt."""

    outcome_id: str
    preparation_id: str
    request_id: str
    merchant_id: str
    capability: CheckoutCapability
    payment_transaction_id: str
    order_status: OrderStatus
    merchant_order_id: Optional[str] = None
    verified_at: str = ""
    order_evidence: Optional[OrderEvidence] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "preparation_id": self.preparation_id,
            "request_id": self.request_id,
            "merchant_id": self.merchant_id,
            "capability": self.capability.value,
            "payment_transaction_id": self.payment_transaction_id,
            "order_status": self.order_status.value,
            "merchant_order_id": self.merchant_order_id,
            "verified_at": self.verified_at,
            "order_evidence": self.order_evidence.to_dict() if self.order_evidence else None,
        }


@dataclass
class CommerceConnectorResult:
    """Result object returned by commerce connectors."""

    connector_id: str
    capability: CheckoutCapability
    status: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "capability": self.capability.value,
            "status": self.status,
            "message": self.message,
            "data": self.data,
        }
