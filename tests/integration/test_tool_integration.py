"""
S02.2 — Tool Capability Registry & M01 Gateway Integration Tests.

Verifies end-to-end flow:
AgentRuntime -> ToolRegistry (CapabilityPolicy) -> Tool Execution -> Proposal Boundary -> M01 Gateway Evaluation.
"""

from datetime import datetime, timezone
from typing import Any
import unittest

from agent.graph.runtime import AgentRuntime
from agent.graph.state import AgentState
from agent.graph.types import AgentConfig, AgentStateEnum
from agent.models.interface import ModelResponse
from agent.models.test_model import TestModelAdapter
from agent.proposal.boundary import AgentProposalBoundary
from agent.tools.capabilities import ToolCapability
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.registry import ToolRegistry
from apps.api.domain.intent_normalizer import IntentNormalizer
from apps.api.domain.mandate import BuyerMandate
from apps.api.domain.merchant import MerchantPolicy
from apps.api.domain.policy_engine import PolicyEngine
from apps.api.domain.types import Currency, MandateStatus, McpOperation, PolicyDecision


class IntegProductTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="integ_product_lookup",
            version="1.0.0",
            description="Integration product lookup",
            input_schema={"sku": "str"},
            output_schema={"item_name": "str", "price_paise": "int"},
            capabilities={ToolCapability.PRODUCT_READ},
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        sku = arguments.get("sku", "SKU_PRO")
        return ToolResult(
            tool_name="integ_product_lookup",
            version="1.0.0",
            success=True,
            data={"item_name": "Smart Watch", "price_paise": 450000, "sku": sku},
        )


class TestToolIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.model_adapter = TestModelAdapter()
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(IntegProductTool())
        self.runtime = AgentRuntime(
            model_adapter=self.model_adapter,
            tool_registry=self.tool_registry,
            config=AgentConfig(max_iterations=10, max_tool_calls=5),
        )

        future_expiry = datetime(2028, 1, 1, tzinfo=timezone.utc)

        # Setup M01 Domain Entities
        self.mandate = BuyerMandate(
            mandate_id="mandate_tool_integ_001",
            buyer_id="buyer_tool_integ_001",
            version=1,
            merchant_scope=frozenset(["merchant_tool_integ_001"]),
            maximum_amount_paise=500000,
            daily_budget_paise=2000000,
            currency=Currency.INR,
            autonomous_execution=True,
            expires_at=future_expiry,
            status=MandateStatus.ACTIVE,
        )
        self.merchant_policy = MerchantPolicy(
            policy_id="policy_tool_integ_001",
            merchant_id="merchant_tool_integ_001",
            policy_version=1,
            ai_commerce_enabled=True,
            currency=Currency.INR,
            autonomous_purchase_limit_paise=500000,
            step_up_threshold_paise=500000,
            max_step_up_percent=10,
            allowed_operations=frozenset([McpOperation.CREATE_ORDER]),
            expires_at=future_expiry,
        )

    def test_agent_tool_invocation_to_m01_evaluation_flow(self) -> None:
        """
        Full Integration Test:
        1. Agent Runtime executes with TestModelAdapter.
        2. Agent calls integ_product_lookup via ToolRegistry.
        3. Agent constructs proposal.
        4. ProposalBoundary builds untrusted proposal.
        5. IntentNormalizer normalizes proposal -> CommerceIntent.
        6. PolicyEngine evaluates CommerceIntent against BuyerMandate and MerchantPolicy -> ALLOW.
        """
        state = AgentState(
            agent_id="ag_tool_integ",
            session_id="session_tool_integ_1",
            buyer_id="buyer_tool_integ_001",
            merchant_id="merchant_tool_integ_001",
            mandate_id="mandate_tool_integ_001",
        )

        # Script Agent turns
        r1 = ModelResponse(
            content="Looking up product",
            tool_calls=[{"name": "integ_product_lookup", "arguments": {"sku": "WATCH_V2"}}],
        )
        r2 = ModelResponse(
            content='{"amount_paise": 450000, "currency": "INR", "operation": "create_order"}',
            finish_reason="stop",
            raw_response={
                "proposal": {"amount_paise": 450000, "currency": "INR", "operation": "create_order"}
            },
        )
        self.model_adapter.set_scripted_responses([r1, r2])

        # Step 1: Run Agent Runtime
        final_state = self.runtime.run(state, "Buy smart watch for 4500 INR")
        self.assertEqual(final_state.current_state, AgentStateEnum.COMPLETED)
        self.assertIsNotNone(final_state.proposal_payload)

        # Step 2: Build Untrusted Proposal
        untrusted_proposal = AgentProposalBoundary.build_proposal(
            session_id=final_state.session_id,
            buyer_id=final_state.buyer_id,
            merchant_id=final_state.merchant_id,
            mandate_id=final_state.mandate_id,
            proposal_data=final_state.proposal_payload or {},
        )
        self.assertFalse(untrusted_proposal.is_trusted, "AI proposal must be untrusted")

        # Step 3: Normalize via M01 IntentNormalizer
        untrusted_dict = AgentProposalBoundary.to_untrusted_dict(untrusted_proposal)
        normalized_proposal = IntentNormalizer.normalize(untrusted_dict)

        # Step 4: Submit to M01 PolicyEngine Evaluation
        now = datetime.now(timezone.utc)
        policy_eval = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=normalized_proposal.cart,
            operation=McpOperation.CREATE_ORDER,
            at=now,
        )

        # Step 5: Verify M01 Deterministic Decision
        self.assertEqual(policy_eval.decision, PolicyDecision.ALLOW)


if __name__ == "__main__":
    unittest.main()
