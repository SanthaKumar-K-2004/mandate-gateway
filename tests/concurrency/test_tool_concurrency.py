"""
S02.2 — Tool Registry Concurrency & State Isolation Tests.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
import unittest

from agent.tools.capabilities import CapabilityPolicy, ToolCapability
from agent.tools.interface import ToolDefinition, ToolInterface, ToolResult
from agent.tools.registry import ToolRegistry


class ConcurrentCatalogTool(ToolInterface):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="concurrent_catalog",
            version="1.0.0",
            description="Concurrent catalog lookup",
            input_schema={"worker_id": "int"},
            output_schema={"status": "str"},
            capabilities={ToolCapability.CATALOG_READ},
            max_invocations=5,  # Per session limit
        )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        w_id = arguments.get("worker_id", 0)
        return ToolResult(
            tool_name="concurrent_catalog",
            version="1.0.0",
            success=True,
            data={"status": f"ok_worker_{w_id}"},
        )


class TestToolConcurrency(unittest.TestCase):
    def test_concurrent_tool_lookups_and_executions(self) -> None:
        """
        Execute 20 concurrent threads running tool lookups and executions
        against a single shared ToolRegistry instance.

        Verifies thread safety and session invocation counter isolation.
        """
        registry = ToolRegistry()
        registry.register(ConcurrentCatalogTool())
        policy = CapabilityPolicy.allow_all_safe()
        num_workers = 20

        def _run_worker(worker_id: int) -> list[ToolResult]:
            worker_results = []
            session_id = f"session_worker_{worker_id}"

            # Execute 3 calls per worker (limit is 5)
            for _ in range(3):
                res = registry.authorize_and_execute(
                    tool_name="concurrent_catalog",
                    arguments={"worker_id": worker_id},
                    capability_policy=policy,
                    session_id=session_id,
                )
                worker_results.append(res)
            return worker_results

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_run_worker, i) for i in range(num_workers)]
            all_worker_results = [future.result() for future in as_completed(futures)]

        self.assertEqual(len(all_worker_results), num_workers)
        for worker_res in all_worker_results:
            self.assertEqual(len(worker_res), 3)
            for r in worker_res:
                self.assertTrue(r.success)
                self.assertIsNotNone(r.data.get("status"))


if __name__ == "__main__":
    unittest.main()
