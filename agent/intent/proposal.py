"""
S02.3 — Untrusted Proposal Construction Engine.

Assembles parsed cart items, merchant ID, buyer ID, mandate ID, and sanitized prompts into
fail-closed ProposalNormalizeRequest payloads for gateway evaluation.
"""

from __future__ import annotations

from typing import Any, List

from agent.intent.errors import IntentErrorCode, IntentValidationError
from agent.intent.parser import AgentIntentParser
from agent.intent.security import PromptInjectionDefense
from apps.api.contracts.intent import ProposalNormalizeRequest
from apps.api.contracts.transaction import CartItemProposal
from apps.api.domain.types import Currency, McpOperation, Region


class AgentProposalBuilder:
    """
    Builder creating validated ProposalNormalizeRequest payloads from untrusted agent outputs.
    """

    @classmethod
    def build_proposal_request(
        cls,
        buyer_id: str,
        merchant_id: str,
        mandate_id: str,
        raw_prompt: str,
        payload: dict[str, Any],
        tax_paise: int = 0,
        shipping_paise: int = 0,
        operation: McpOperation = McpOperation.CREATE_ORDER,
        metadata: dict[str, Any] | None = None,
    ) -> ProposalNormalizeRequest:
        """
        Build a fail-closed ProposalNormalizeRequest DTO payload.
        """
        # 1. Mandatory Identifier Validations
        if not buyer_id or not buyer_id.strip():
            raise IntentValidationError(IntentErrorCode.MISSING_MANDATORY_FIELD, "buyer_id cannot be empty.")
        if not merchant_id or not merchant_id.strip():
            raise IntentValidationError(IntentErrorCode.MISSING_MANDATORY_FIELD, "merchant_id cannot be empty.")
        if not mandate_id or not mandate_id.strip():
            raise IntentValidationError(IntentErrorCode.MISSING_MANDATORY_FIELD, "mandate_id cannot be empty.")

        # 2. Sanitize Raw Prompt Text
        sanitized_prompt = PromptInjectionDefense.sanitize_text(raw_prompt)
        if not sanitized_prompt or not sanitized_prompt.strip():
            sanitized_prompt = "Purchase intent proposal"

        # 3. Parse Items & Verify Arithmetic Math
        parsed_items: List[CartItemProposal] = AgentIntentParser.parse_intent_payload(
            payload=payload,
            default_merchant_id=merchant_id.strip(),
        )

        total_items_paise = sum(item.quantity * item.unit_price_paise for item in parsed_items)
        grand_total_paise = total_items_paise + tax_paise + shipping_paise

        # 4. Construct ProposalNormalizeRequest DTO
        return ProposalNormalizeRequest(
            buyer_id=buyer_id.strip(),
            merchant_id=merchant_id.strip(),
            mandate_id=mandate_id.strip(),
            raw_prompt=sanitized_prompt,
            items=parsed_items,
            operation=operation,
            currency=Currency.INR,
            region=Region.IN,
            tax_paise=tax_paise,
            shipping_paise=shipping_paise,
            total_paise=grand_total_paise,
            metadata=metadata or {},
        )
