"""
S02.3 — Gateway Integration Adapter.

Bridges AgentState graph payloads from S02.1/S02.2 into M01 IntentNormalizer
to produce canonical NormalizedCommerceProposal objects for PolicyEngine evaluation.
"""

from __future__ import annotations

from typing import Any

from agent.graph.state import AgentState
from agent.intent.errors import IntentErrorCode, IntentValidationError
from agent.intent.observability import IntentAuditLogger
from agent.intent.proposal import AgentProposalBuilder
from apps.api.domain.intent_normalizer import IntentNormalizer, NormalizedCommerceProposal


class GatewayAdapter:
    """
    Adapter bridging Agent runtime graph outputs into the trusted M01 Gateway Intent Normalizer.
    """

    @classmethod
    def normalize_agent_state(
        cls,
        state: AgentState,
        raw_prompt: str = "",
    ) -> NormalizedCommerceProposal:
        """
        Extract proposal payload from AgentState, construct validated request DTO,
        and run M01 IntentNormalizer.normalize().
        """
        payload: dict[str, Any] = state.proposal_payload or {}
        if not payload:
            IntentAuditLogger.log_event("rejected", session_id=state.session_id, detail="Empty proposal payload in AgentState.")
            raise IntentValidationError(
                IntentErrorCode.MISSING_MANDATORY_FIELD,
                "AgentState contains no proposal payload to normalize.",
            )

        IntentAuditLogger.log_event("parsed", session_id=state.session_id)

        # 1. Build Proposal Normalize Request DTO
        request_dto = AgentProposalBuilder.build_proposal_request(
            buyer_id=state.buyer_id,
            merchant_id=state.merchant_id,
            mandate_id=state.mandate_id,
            raw_prompt=raw_prompt or state.user_input or "Agent commerce request",
            payload=payload,
            metadata={"session_id": state.session_id, "agent_id": state.agent_id},
        )

        # 2. Convert DTO to dict for untrusted normalization
        untrusted_dict = request_dto.model_dump()

        # 3. Trigger Trusted M01 Gateway Normalization
        normalized_proposal = IntentNormalizer.normalize(untrusted_dict)
        IntentAuditLogger.log_event("normalized", session_id=state.session_id)

        return normalized_proposal
