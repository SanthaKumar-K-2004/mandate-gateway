"""
S02.1 — Agent Proposal Boundary.

Constructs untrusted CommerceIntent proposals from agent planning payloads
for submission to M01 Gateway evaluation boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from apps.api.contracts.intent import ProposalNormalizeRequest
from apps.api.contracts.transaction import CartItemProposal
from apps.api.domain.money import Money
from apps.api.domain.types import Currency, McpOperation, Region


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True, slots=True)
class AgentProposal:
    """
    Untrusted proposal constructed by AI Agent runtime.

    MUST be evaluated by M01 Gateway before authorization or execution.
    """

    proposal_id: str
    session_id: str
    buyer_id: str
    merchant_id: str
    mandate_id: str
    operation: McpOperation
    amount_paise: int
    currency: Currency
    cart_id: str
    cart_hash: str
    raw_prompt: str
    items: list[dict[str, Any]] = field(default_factory=list)
    is_trusted: bool = False  # NEVER True for AI-generated proposals
    created_at: datetime = field(default_factory=_utc_now)


class AgentProposalBoundary:
    """
    Boundary converting agent graph state into untrusted proposal payloads.
    """

    @classmethod
    def build_proposal(
        cls,
        session_id: str,
        buyer_id: str,
        merchant_id: str,
        mandate_id: str,
        proposal_data: dict[str, Any],
    ) -> AgentProposal:
        """
        Build an untrusted AgentProposal from graph payload.

        Guarantees is_trusted=False.
        """
        amount = proposal_data.get("amount_paise", 1000)
        curr_str = proposal_data.get("currency", "INR")
        op_str = proposal_data.get("operation", "create_order")
        cart_id = proposal_data.get("cart_id", f"cart_{session_id[:8]}")
        cart_hash = proposal_data.get(
            "cart_hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        raw_prompt = proposal_data.get("raw_prompt", "AI Commerce Agent Proposal")
        items_data = proposal_data.get(
            "items",
            [
                {
                    "product_id": f"prod_{session_id[:8]}",
                    "name": "Proposed Commerce Item",
                    "quantity": 1,
                    "unit_price_paise": amount,
                }
            ],
        )

        currency = Currency(curr_str.upper()) if isinstance(curr_str, str) else Currency.INR
        operation = (
            McpOperation(op_str.lower()) if isinstance(op_str, str) else McpOperation.CREATE_ORDER
        )

        return AgentProposal(
            proposal_id=f"prop_{session_id[:8]}",
            session_id=session_id,
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            mandate_id=mandate_id,
            operation=operation,
            amount_paise=amount,
            currency=currency,
            cart_id=cart_id,
            cart_hash=cart_hash,
            raw_prompt=raw_prompt,
            items=items_data,
            is_trusted=False,  # ALWAYS UNTRUSTED
        )

    @classmethod
    def to_normalize_request(cls, proposal: AgentProposal) -> ProposalNormalizeRequest:
        """Convert AgentProposal into M01 ProposalNormalizeRequest DTO."""
        item_proposals = [
            CartItemProposal(
                product_id=it.get("product_id", "prod_001"),
                name=it.get("name", "Proposed Item"),
                quantity=it.get("quantity", 1),
                unit_price_paise=it.get("unit_price_paise", proposal.amount_paise),
                currency=proposal.currency,
            )
            for it in proposal.items
        ]
        return ProposalNormalizeRequest(
            buyer_id=proposal.buyer_id,
            merchant_id=proposal.merchant_id,
            mandate_id=proposal.mandate_id,
            raw_prompt=proposal.raw_prompt,
            items=item_proposals,
            operation=proposal.operation,
            currency=proposal.currency,
            region=Region.IN,
            total_paise=proposal.amount_paise,
        )

    @classmethod
    def to_untrusted_dict(cls, proposal: AgentProposal) -> dict[str, Any]:
        """Convert AgentProposal into untrusted dict representation."""
        return {
            "buyer_id": proposal.buyer_id,
            "merchant_id": proposal.merchant_id,
            "mandate_id": proposal.mandate_id,
            "raw_prompt": proposal.raw_prompt,
            "operation": proposal.operation.value,
            "currency": proposal.currency.value,
            "amount_paise": proposal.amount_paise,
            "items": [
                {
                    "product_id": it.get("product_id", "prod_001"),
                    "name": it.get("name", "Proposed Item"),
                    "quantity": it.get("quantity", 1),
                    "unit_price_paise": it.get("unit_price_paise", proposal.amount_paise),
                    "currency": proposal.currency.value,
                }
                for it in proposal.items
            ],
            "is_trusted": False,
        }
