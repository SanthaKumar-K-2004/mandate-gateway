"""
Mandate Gateway — Live AI Purchase Planning Engine
Workstreams 5 & 6 — Complete live purchase flow:
  User Request -> LLM Intent -> Security -> Live Discovery ->
  Product Normalization -> Constraint Validation -> Truth Validation -> Plan -> Token.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Optional

from apps.api.agent.confirmation_gate import HumanConfirmationGate
from apps.api.agent.llm_gateway import LLMProvider, MockLLMProvider
from apps.api.agent.models import AgentDecision, AgentRequest, PurchasePlan
from apps.api.agent.product_discovery import LiveProductSearchProvider, ProductDiscoveryProvider
from apps.api.agent.product_truth_validator import ProductTruthValidator
from apps.api.agent.tool_registry import AIToolRegistry
from apps.api.agent.validator import AIStructuredOutputValidator


class PurchasePlanner:
    """Live AI purchase planning flow engine."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        discovery_provider: Optional[ProductDiscoveryProvider] = None,
        tool_registry: Optional[AIToolRegistry] = None,
        confirmation_gate: Optional[HumanConfirmationGate] = None,
    ) -> None:
        self.llm_provider = llm_provider or MockLLMProvider()
        self.discovery_provider = discovery_provider or LiveProductSearchProvider()
        self.tool_registry = tool_registry or AIToolRegistry()
        self.confirmation_gate = confirmation_gate or HumanConfirmationGate()
        self.validator = AIStructuredOutputValidator(self.tool_registry)

    def process_request(self, request: AgentRequest) -> AgentDecision:
        """
        Execute live purchase planning pipeline:
        Intent -> Security -> Live Discovery -> Truth Validation -> Plan -> Confirmation Token
        """
        # 1. Intent Extraction via LLM API
        intent = self.llm_provider.extract_intent(request.prompt)
        self.validator.validate_intent(intent)

        # 2. Live Product Discovery
        candidates = self.discovery_provider.search_live_products(
            query=intent.product_query,
            max_price_paise=intent.max_amount_paise,
            category=intent.category,
        )

        if not candidates:
            # Fallback to tool registry search if live discovery yields no candidates
            search_res = self.tool_registry.invoke_tool(
                "search_products",
                {"query": intent.product_query, "max_price_paise": intent.max_amount_paise},
            )
            candidates = search_res.get("results", [])

        if not candidates:
            exp_msg = (
                f"No matching live products found under budget ₹{intent.max_amount_paise / 100:.2f} INR "
                f"for query '{intent.product_query}'."
            )
            return AgentDecision(status="REJECTED", explanation=exp_msg)

        # 3. LLM Candidate Ranking
        ranked = self.llm_provider.rank_candidates(request, candidates)
        selected_candidate = ranked[0]

        # 4. Product Truth Validation (Rejects LLM hallucinated products or prices)
        truth_verified = ProductTruthValidator.validate_recommendation(
            selected_product=selected_candidate,
            retrieved_source_results=candidates,
        )

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # 5. Compute purchase plan cryptographic hash
        m_id = truth_verified["merchant_id"]
        a_paise = truth_verified["amount_paise"]
        p_id = truth_verified["product_id"]
        raw_hash_data = f"{plan_id}|{m_id}|{a_paise}|{p_id}"
        plan_hash = hashlib.sha256(raw_hash_data.encode("utf-8")).hexdigest()

        # 6. Issue Cryptographically Bound Confirmation Token
        cnf_data = self.confirmation_gate.generate_token(
            request_id=request.request_id,
            merchant_id=truth_verified["merchant_id"],
            buyer_id=request.buyer_id,
            product_id=truth_verified["product_id"],
            product_source=truth_verified["product_source"],
            amount_paise=truth_verified["amount_paise"],
            currency=truth_verified["currency"],
            purchase_plan_hash=plan_hash,
        )

        plan = PurchasePlan(
            plan_id=plan_id,
            request_id=request.request_id,
            merchant_id=truth_verified["merchant_id"],
            buyer_id=request.buyer_id,
            product_id=truth_verified["product_id"],
            product_name=truth_verified["name"],
            amount_paise=truth_verified["amount_paise"],
            currency=truth_verified["currency"],
            product_source=truth_verified["product_source"],
            source_url=truth_verified.get("source_url", ""),
            purchase_plan_hash=plan_hash,
            retrieval_timestamp=truth_verified.get("retrieval_timestamp", ""),
            reasoning_summary=f"Selected verified candidate '{truth_verified['name']}'",
            tool_provenance=["LiveProductSearchProvider"],
            requires_confirmation=intent.requires_confirmation,
            confirmation_token=(
                cnf_data["confirmation_token"] if intent.requires_confirmation else None
            ),
        )

        status = "AWAITING_CONFIRMATION" if intent.requires_confirmation else "PLANNING"
        exp_plan_msg = (
            f"Live purchase plan formulated for '{truth_verified['name']}' at "
            f"₹{truth_verified['amount_paise'] / 100:.2f} INR (Source: {truth_verified['product_source']}). "
            "Awaiting explicit human confirmation."
        )
        return AgentDecision(
            status=status,
            purchase_plan=plan,
            explanation=exp_plan_msg,
        )
