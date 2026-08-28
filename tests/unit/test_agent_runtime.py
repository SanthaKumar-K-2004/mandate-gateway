"""
S02.1 — Agent Runtime & Bounded Loop Execution Unit Tests.
"""

from typing import Any
import unittest

from agent.graph.errors import (
    AgentCancellationError,
    AgentLoopLimitExceededError,
    AgentSecurityViolationError,
    AgentToolLimitExceededError,
)
from agent.graph.runtime import AgentRuntime
from agent.graph.state import AgentState
from agent.graph.types import AgentConfig, AgentStateEnum
from agent.models.interface import ModelResponse
from agent.models.test_model import TestModelAdapter
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.registry import ToolRegistry


class DummySearchTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_items",
            description="Search merchant inventory",
            input_schema={"query": "str"},
            output_schema={"found": "bool"},
            max_invocations=5,
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            tool_name="search_items",
            success=True,
            data={"found": True, "query": arguments.get("query")},
        )


class TestAgentRuntimeUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.model_adapter = TestModelAdapter()
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_tool(DummySearchTool())
        self.config = AgentConfig(max_iterations=10, max_tool_calls=5, timeout_seconds=5.0)
        self.runtime = AgentRuntime(
            model_adapter=self.model_adapter,
            tool_registry=self.tool_registry,
            config=self.config,
        )

    def test_successful_proposal_flow(self) -> None:
        """Test full graph run culminating in proposal generation."""
        state = AgentState(
            agent_id="ag_1",
            session_id="sess_1",
            buyer_id="b_1",
            merchant_id="m_1",
            mandate_id="man_1",
        )
        r1 = ModelResponse(
            content='{"amount_paise": 4900, "currency": "INR", "operation": "create_order"}',
            finish_reason="stop",
            raw_response={
                "proposal": {"amount_paise": 4900, "currency": "INR", "operation": "create_order"}
            },
        )
        self.model_adapter.set_scripted_responses([r1])

        res_state = self.runtime.run(state, "Buy noise cancelling headphones under 5000")
        self.assertEqual(res_state.current_state, AgentStateEnum.COMPLETED)
        self.assertIsNotNone(res_state.proposal_payload)
        assert res_state.proposal_payload is not None
        self.assertEqual(res_state.proposal_payload.get("amount_paise"), 4900)

    def test_max_iterations_exceeded(self) -> None:
        """Test loop limit breach raises AgentLoopLimitExceededError."""
        low_config = AgentConfig(max_iterations=2, max_tool_calls=5, timeout_seconds=5.0)
        runtime = AgentRuntime(self.model_adapter, self.tool_registry, low_config)
        state = AgentState("ag_1", "sess_1", "b_1", "m_1", "man_1")

        # Script responses that continuously call tools without stopping
        self.model_adapter.set_response_generator(
            lambda req: ModelResponse(
                content="Iterating...",
                tool_calls=[
                    {"name": "search_items", "arguments": {"query": f"q_{len(req.messages)}"}}
                ],
            )
        )

        with self.assertRaises(AgentLoopLimitExceededError):
            runtime.run(state, "Infinite loop test")

    def test_max_tool_calls_exceeded(self) -> None:
        """Test tool call limit breach raises AgentToolLimitExceededError."""
        low_config = AgentConfig(max_iterations=10, max_tool_calls=1, timeout_seconds=5.0)
        runtime = AgentRuntime(self.model_adapter, self.tool_registry, low_config)
        state = AgentState("ag_1", "sess_1", "b_1", "m_1", "man_1")

        # Script 2 tool calls sequentially
        r1 = ModelResponse(
            content="Tool 1", tool_calls=[{"name": "search_items", "arguments": {"query": "q1"}}]
        )
        r2 = ModelResponse(
            content="Tool 2", tool_calls=[{"name": "search_items", "arguments": {"query": "q2"}}]
        )
        self.model_adapter.set_scripted_responses([r1, r2])

        with self.assertRaises(AgentToolLimitExceededError):
            runtime.run(state, "Tool limit test")

    def test_cancellation_token(self) -> None:
        """Test cancellation signal stops runtime immediately."""
        state = AgentState("ag_1", "sess_1", "b_1", "m_1", "man_1")
        token = {"cancelled": True}

        with self.assertRaises(AgentCancellationError):
            self.runtime.run(state, "Cancelled request", cancellation_token=token)
        self.assertEqual(state.current_state, AgentStateEnum.CANCELLED)

    def test_infinite_tool_loop_detection(self) -> None:
        """Test 3 identical tool calls in sequence triggers infinite loop detection."""
        state = AgentState("ag_1", "sess_1", "b_1", "m_1", "man_1")
        same_call = {"name": "search_items", "arguments": {"query": "duplicate"}}

        self.model_adapter.set_response_generator(
            lambda req: ModelResponse(content="Repeat", tool_calls=[same_call])
        )

        with self.assertRaises(AgentSecurityViolationError) as ctx:
            self.runtime.run(state, "Infinite loop tool test")
        self.assertIn("Infinite loop detected", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
