"""
S02.3 — AI Intent Normalization & M01 Gateway Integration Tests.

Verifies complete flow:
AgentRuntime -> Tool Execution -> GatewayAdapter -> IntentNormalizer -> PolicyEngine (ALLOW).
"""

from datetime import datetime, timezone
from typing import Any
import unittest

from agent.graph.runtime import AgentRuntime
from agent.graph.state import AgentState
from agent.graph.types import AgentConfig, AgentStateEnum
from agent.intent.gateway_adapter import GatewayAdapter
from agent.models.interface import ModelResponse
from agent.models.test_model import TestModelAdapter
from agent.tools.capabilities import ToolCapability
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.registry import ToolRegistry
from apps.api.domain.mandate import BuyerMandate
from apps.api.domain.merchant import MerchantPolicy
from apps.api.domain.policy_engine import PolicyEngine
from apps.api.domain.types import Currency, MandateStatus, McpOperation, PolicyDecision


class IntegSearchTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="integ_search_tool",
            version="1.0.0",
            description="Integration search tool",
            input_schema={"query": "str"},
            output_schema={"items": "list"},
            capabilities={ToolCapability.PRODUCT_READ},
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            tool_name="integ_search_tool",
            version="1.0.0",
            success=True,
            data={
                "items": [
                    {"product_id": "P_DESK_01", "name": "Standing Desk", "price_paise": 2500000}
                ]
            },
        )


class TestIntentIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.model_adapter = TestModelAdapter()
        self.tool_registry = ToolRegistry()
        self.tool_registry.register(IntegSearchTool())
        self.runtime = AgentRuntime(
            model_adapter=self.model_adapter,
            tool_registry=self.tool_registry,
            config=AgentConfig(max_iterations=10, max_tool_calls=5),
        )

        future_expiry = datetime(2028, 1, 1, tzinfo=timezone.utc)

        # M01 Domain Entities
        self.mandate = BuyerMandate(
            mandate_id="mandate_intent_integ_001",
            buyer_id="buyer_intent_integ_001",
            version=1,
            merchant_scope=frozenset(["merchant_intent_integ_001"]),
            maximum_amount_paise=3000000,
            daily_budget_paise=5000000,
            currency=Currency.INR,
            autonomous_execution=True,
            expires_at=future_expiry,
            status=MandateStatus.ACTIVE,
        )
        self.merchant_policy = MerchantPolicy(
            policy_id="policy_intent_integ_001",
            merchant_id="merchant_intent_integ_001",
            policy_version=1,
            ai_commerce_enabled=True,
            currency=Currency.INR,
            autonomous_purchase_limit_paise=3000000,
            step_up_threshold_paise=3000000,
            max_step_up_percent=10,
            allowed_operations=frozenset([McpOperation.CREATE_ORDER]),
            expires_at=future_expiry,
        )

    def test_agent_intent_normalization_to_m01_evaluation_flow(self) -> None:
        """
        Full Integration Test:
        1. Agent Runtime executes with TestModelAdapter.
        2. Agent calls integ_search_tool via ToolRegistry.
        3. Agent produces raw proposal payload.
        4. GatewayAdapter.normalize_agent_state() validates intent, parses items,
           verifies arithmetic math, checks prompt injection, and calls M01 IntentNormalizer.
        5. PolicyEngine evaluates CommerceIntent against BuyerMandate and MerchantPolicy -> ALLOW.
        """
        state = AgentState(
            agent_id="ag_intent_integ",
            session_id="session_intent_integ_1",
            buyer_id="buyer_intent_integ_001",
            merchant_id="merchant_intent_integ_001",
            mandate_id="mandate_intent_integ_001",
        )

        # Script Agent turns
        r1 = ModelResponse(
            content="Searching catalog for desk",
            tool_calls=[{"name": "integ_search_tool", "arguments": {"query": "standing desk"}}],
        )
        r2_content = (
            '{"merchant_id": "merchant_intent_integ_001", "items": ['
            '{"product_id": "P_DESK_01", "name": "Standing Desk", '
            '"quantity": 1, "unit_price_paise": 2500000, "subtotal_paise": 2500000}]}'
        )
        r2 = ModelResponse(
            content=r2_content,
            finish_reason="stop",
            raw_response={
                "proposal": {
                    "merchant_id": "merchant_intent_integ_001",
                    "currency": "INR",
                    "items": [
                        {
                            "product_id": "P_DESK_01",
                            "name": "Standing Desk",
                            "quantity": 1,
                            "unit_price_paise": 2500000,
                            "subtotal_paise": 2500000,
                        }
                    ],
                }
            },
        )
        self.model_adapter.set_scripted_responses([r1, r2])

        # Step 1: Execute Agent Runtime
        final_state = self.runtime.run(state, "Buy standing desk for 25000 INR")
        self.assertEqual(final_state.current_state, AgentStateEnum.COMPLETED)
        self.assertIsNotNone(final_state.proposal_payload)

        # Step 2: Gateway Adapter Normalizes Agent State
        normalized_proposal = GatewayAdapter.normalize_agent_state(
            state=final_state,
            raw_prompt="Buy standing desk for 25000 INR",
        )
        self.assertEqual(normalized_proposal.intent.target_merchant_id, "merchant_intent_integ_001")
        self.assertEqual(normalized_proposal.cart.total_paise, 2500000)

        # Step 3: PolicyEngine Evaluation
        now = datetime.now(timezone.utc)
        policy_eval = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=normalized_proposal.cart,
            operation=McpOperation.CREATE_ORDER,
            at=now,
        )

        # Step 4: Verify Decision is ALLOW
        self.assertEqual(policy_eval.decision, PolicyDecision.ALLOW)


if __name__ == "__main__":
    unittest.main()
