"""
S02.1 — Agent Runtime Concurrency & State Isolation Tests.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
import unittest

from agent.graph.runtime import AgentRuntime
from agent.graph.state import AgentState
from agent.graph.types import AgentConfig, AgentStateEnum
from agent.models.interface import ModelResponse
from agent.models.test_model import TestModelAdapter
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.registry import ToolRegistry


class ConcurrentDummyTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="concurrent_tool",
            description="Tool for concurrency testing",
            input_schema={"worker_id": "int"},
            output_schema={"result": "str"},
            max_invocations=50,
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        w_id = arguments.get("worker_id", 0)
        return ToolResult(
            tool_name="concurrent_tool",
            success=True,
            data={"result": f"processed_by_worker_{w_id}"},
        )


class TestAgentConcurrency(unittest.TestCase):
    def test_parallel_agent_execution_isolation(self) -> None:
        """
        Execute 20 concurrent threads running independent AgentRuntime instances.

        Verifies zero state cross-contamination and 100% execution isolation.
        """
        num_workers = 20
        results: list[AgentState] = []

        def _run_worker(worker_id: int) -> AgentState:
            adapter = TestModelAdapter()
            registry = ToolRegistry()
            registry.register_tool(ConcurrentDummyTool())
            runtime = AgentRuntime(
                model_adapter=adapter,
                tool_registry=registry,
                config=AgentConfig(max_iterations=10, max_tool_calls=5),
            )
            state = AgentState(
                agent_id=f"agent_{worker_id}",
                session_id=f"session_{worker_id}",
                buyer_id=f"buyer_{worker_id}",
                merchant_id=f"merchant_{worker_id}",
                mandate_id=f"mandate_{worker_id}",
            )

            r1 = ModelResponse(
                content=f"Worker {worker_id} tool request",
                tool_calls=[{"name": "concurrent_tool", "arguments": {"worker_id": worker_id}}],
            )
            r2 = ModelResponse(
                content=f'{{"amount_paise": {1000 + worker_id}, "currency": "INR", "operation": "create_order"}}',
                finish_reason="stop",
                raw_response={
                    "proposal": {
                        "amount_paise": 1000 + worker_id,
                        "currency": "INR",
                        "operation": "create_order",
                    }
                },
            )
            adapter.set_scripted_responses([r1, r2])

            return runtime.run(state, f"Worker {worker_id} execution request")

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_run_worker, i) for i in range(num_workers)]
            for future in as_completed(futures):
                results.append(future.result())

        self.assertEqual(len(results), num_workers)
        for state in results:
            self.assertEqual(state.current_state, AgentStateEnum.COMPLETED)
            # Extract worker ID from agent_id
            w_id = int(state.agent_id.split("_")[1])
            self.assertEqual(state.buyer_id, f"buyer_{w_id}")
            self.assertEqual(state.merchant_id, f"merchant_{w_id}")
            self.assertEqual(state.mandate_id, f"mandate_{w_id}")
            self.assertIsNotNone(state.proposal_payload)
            assert state.proposal_payload is not None
            self.assertEqual(state.proposal_payload.get("amount_paise"), 1000 + w_id)


if __name__ == "__main__":
    unittest.main()
