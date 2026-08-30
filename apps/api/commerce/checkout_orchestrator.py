"""
Mandate Gateway — Checkout Orchestrator (M24)
Workstream 11 — Orchestrates the complete end-to-end commerce lifecycle:
Truth Evaluation -> Capability Resolution -> Price Revalidation -> Availability Revalidation
-> Checkout Preparation -> Outcome Verification.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict, Optional, Tuple

from apps.api.agent.confirmation_gate import HumanConfirmationGate
from apps.api.commerce.audit import CommerceAuditLogger
from apps.api.commerce.availability_revalidation import LiveAvailabilityRevalidator
from apps.api.commerce.connector_registry import CommerceConnectorRegistry
from apps.api.commerce.connector_resolver import CheckoutCapabilityResolver
from apps.api.commerce.models import (
    CheckoutCapability,
    CheckoutPreparation,
    ProductVerificationStatus,
)
from apps.api.commerce.order_verification import OrderVerificationEngine
from apps.api.commerce.price_revalidation import LivePriceRevalidator
from apps.api.commerce.product_truth_engine import ProductTruthEngine
from apps.api.commerce.redirect_handoff import SecureRedirectHandoffManager


class CheckoutOrchestratorError(RuntimeError):
    """Raised when Checkout Orchestrator processing fails."""

    pass


class CheckoutOrchestrator:
    """Production-grade Checkout Orchestrator."""

    def __init__(
        self,
        confirmation_gate: Optional[HumanConfirmationGate] = None,
        registry: Optional[CommerceConnectorRegistry] = None,
    ) -> None:
        self.confirmation_gate = confirmation_gate or HumanConfirmationGate()
        self.registry = registry or CommerceConnectorRegistry()
        self.capability_resolver = CheckoutCapabilityResolver(self.registry)
        self.handoff_manager = SecureRedirectHandoffManager()
        self.order_verifier = OrderVerificationEngine()

    def prepare_checkout_flow(
        self,
        request_id: str,
        buyer_id: str,
        raw_candidate: Dict[str, Any],
        live_recheck_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, CheckoutPreparation, str]:
        """
        Execute full preparation flow:
        1. Evaluate Product Truth
        2. Resolve Checkout Capability
        3. Live Price Revalidation
        4. Live Availability Revalidation
        5. Package Preparation & Token Generation
        Returns: (success: bool, preparation: CheckoutPreparation, message: str)
        """
        # 1. Product Truth Evaluation
        truth = ProductTruthEngine.evaluate_product(raw_candidate)
        product = truth.product

        CommerceAuditLogger.log_event("PRODUCT_TRUTH_EVALUATED", truth.to_dict())

        if product.verification_status == ProductVerificationStatus.UNVERIFIED:
            prep_id = f"prep_rejected_{uuid.uuid4().hex[:8]}"
            rejected_prep = CheckoutPreparation(
                preparation_id=prep_id,
                request_id=request_id,
                merchant_id=product.merchant.merchant_id,
                buyer_id=buyer_id,
                product=product,
                capability=CheckoutCapability.UNSUPPORTED,
                handoff_url=None,
                confirmation_token=None,
                expires_at="",
                plan_hash="",
            )
            return (
                False,
                rejected_prep,
                f"Product truth validation failed: {'; '.join(truth.validation_errors)}",
            )

        # 2. Capability Resolution
        capability, capability_msg = self.capability_resolver.resolve_capability(product)
        CommerceAuditLogger.log_event(
            "CAPABILITY_RESOLVED",
            {"product_id": product.product_id, "capability": capability.value},
        )

        # 3. Live Price Revalidation
        price_valid, current_price, price_changed = LivePriceRevalidator.revalidate(
            product, live_recheck_data
        )
        CommerceAuditLogger.log_event(
            "PRICE_REVALIDATED", {"product_id": product.product_id, "price_changed": price_changed}
        )

        if price_changed:
            product.verification_status = ProductVerificationStatus.PRICE_CHANGED
            prep_id = f"prep_price_changed_{uuid.uuid4().hex[:8]}"
            mutated_prep = CheckoutPreparation(
                preparation_id=prep_id,
                request_id=request_id,
                merchant_id=product.merchant.merchant_id,
                buyer_id=buyer_id,
                product=product,
                capability=capability,
                handoff_url=None,
                confirmation_token=None,
                expires_at="",
                plan_hash="",
            )
            return (
                False,
                mutated_prep,
                (
                    "Live price revalidation detected a price mutation! "
                    f"Original: ₹{product.price.amount_paise/100:.2f}, "
                    f"Current: ₹{current_price.amount_paise/100:.2f}. "
                    "Old confirmation invalidated."
                ),
            )

        # 4. Live Availability Revalidation
        stock_valid, stock_ev = LiveAvailabilityRevalidator.revalidate(product, live_recheck_data)
        if not stock_valid:
            product.verification_status = ProductVerificationStatus.OUT_OF_STOCK
            prep_id = f"prep_stock_rejected_{uuid.uuid4().hex[:8]}"
            stock_prep = CheckoutPreparation(
                preparation_id=prep_id,
                request_id=request_id,
                merchant_id=product.merchant.merchant_id,
                buyer_id=buyer_id,
                product=product,
                capability=capability,
                handoff_url=None,
                confirmation_token=None,
                expires_at="",
                plan_hash="",
            )
            return (
                False,
                stock_prep,
                "Product is currently OUT_OF_STOCK. Checkout preparation rejected.",
            )

        # 5. Package Preparation & Token Generation
        prep_id = f"prep_{uuid.uuid4().hex[:8]}"

        # Compute cryptographic plan hash
        m_id = product.merchant.merchant_id
        a_paise = product.price.amount_paise
        p_id = product.product_id
        raw_hash_data = f"{prep_id}|{m_id}|{a_paise}|{p_id}"
        plan_hash = hashlib.sha256(raw_hash_data.encode("utf-8")).hexdigest()

        # Generate Cryptographic Confirmation Token
        cnf_data = self.confirmation_gate.generate_token(
            request_id=request_id,
            merchant_id=product.merchant.merchant_id,
            buyer_id=buyer_id,
            product_id=product.product_id,
            product_source=product.verification_status.value,
            amount_paise=product.price.amount_paise,
            currency=product.price.currency,
            purchase_plan_hash=plan_hash,
        )

        # Construct Handoff Package for CHECKOUT_HANDOFF
        handoff_url = None
        if capability == CheckoutCapability.CHECKOUT_HANDOFF:
            pkg = self.handoff_manager.create_handoff_package(request_id, buyer_id, product)
            handoff_url = pkg["handoff_url"]

        preparation = CheckoutPreparation(
            preparation_id=prep_id,
            request_id=request_id,
            merchant_id=product.merchant.merchant_id,
            buyer_id=buyer_id,
            product=product,
            capability=capability,
            handoff_url=handoff_url,
            confirmation_token=cnf_data["confirmation_token"],
            expires_at=cnf_data["expires_at"],
            plan_hash=plan_hash,
        )

        # Record initial outcome tracking state
        self.order_verifier.record_checkout_intent(
            preparation_id=prep_id,
            request_id=request_id,
            merchant_id=product.merchant.merchant_id,
            capability_str=capability.value,
        )

        CommerceAuditLogger.log_event("PREPARATION_COMPLETED", preparation.to_dict())

        return True, preparation, capability_msg
