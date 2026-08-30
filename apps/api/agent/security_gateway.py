"""
Mandate Gateway — AI Security Gateway & Threat Defense
Workstream 8 — Multi-layered defense evaluating prompt injection, instruction hierarchy attacks,
tool result poisoning, confirmation bypass attempts, and cross-tenant data requests.
Enforces deterministic security boundaries: Prompt filtering alone is NOT a security boundary.
"""

from __future__ import annotations

import re
from typing import Optional

from apps.api.agent.confirmation_gate import HumanConfirmationGate
from apps.api.agent.models import PurchasePlan
from apps.api.agent.validator import AIStructuredOutputValidator


class AISecurityThreatDetected(ValueError):
    """Raised when an adversarial AI prompt injection or confirmation bypass attempt is detected."""

    pass


class AISecurityGateway:
    """AI security gateway enforcing multi-layer threat defense."""

    def __init__(
        self,
        validator: Optional[AIStructuredOutputValidator] = None,
        confirmation_gate: Optional[HumanConfirmationGate] = None,
    ) -> None:
        self.validator = validator or AIStructuredOutputValidator()
        self.confirmation_gate = confirmation_gate or HumanConfirmationGate()

    def inspect_prompt(self, prompt: str) -> str:
        """
        Inspect natural language prompt for malicious injection patterns.
        Note: Prompt inspection is a defense-in-depth layer, NOT the primary security boundary.
        """
        p_lower = prompt.lower()
        injection_patterns = [
            r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
            r"bypass\s+confirmation",
            r"override\s+budget",
            r"system_prompt_override",
            r"admin_mode_enable",
        ]
        for pattern in injection_patterns:
            if re.search(pattern, p_lower):
                raise AISecurityThreatDetected(
                    f"Prompt injection pattern detected: '{pattern}'. Request rejected."
                )
        return prompt

    def validate_plan_execution_boundary(
        self,
        plan: PurchasePlan,
        confirmation_token: str,
        authenticated_merchant_id: str,
    ) -> bool:
        """
        Enforces deterministic security boundary prior to payment execution:
        1. Tenant isolation: Plan merchant_id must match authenticated merchant_id.
        2. Confirmation token: Must be cryptographically valid, matching request, amount, merchant, and unconsumed.
        """
        if plan.merchant_id != authenticated_merchant_id:
            raise AISecurityThreatDetected(
                f"Cross-tenant IDOR attack detected: PurchasePlan merchant '{plan.merchant_id}' "
                f"does not match authenticated merchant '{authenticated_merchant_id}'."
            )

        if plan.requires_confirmation:
            if not confirmation_token:
                raise AISecurityThreatDetected(
                    "Payment execution rejected: Missing human confirmation token."
                )

            # Validate cryptographic token binding
            self.confirmation_gate.verify_and_consume_token(
                confirmation_token=confirmation_token,
                request_id=plan.request_id,
                merchant_id=plan.merchant_id,
                buyer_id=plan.buyer_id,
                amount_paise=plan.amount_paise,
                currency=plan.currency,
                product_id=plan.product_id,
                product_source=plan.product_source,
                purchase_plan_hash=plan.purchase_plan_hash,
            )

        return True
