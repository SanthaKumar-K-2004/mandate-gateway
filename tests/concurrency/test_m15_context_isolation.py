"""
Concurrency tests for M15 Observability Context Isolation.
"""

import asyncio
import unittest

from apps.api.app.context import (
    clear_request_context,
    get_full_context,
    set_request_context,
    set_transaction_context,
)


class TestM15ContextIsolationConcurrency(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_tasks_have_strict_context_isolation(self) -> None:
        """Verify 50 concurrent async tasks maintain strictly isolated request and transaction contexts."""

        async def worker(worker_id: int) -> dict:
            clear_request_context()
            req_id = f"req_worker_{worker_id}"
            tx_id = f"tx_worker_{worker_id}"
            set_request_context(req_id)
            set_transaction_context(transaction_id=tx_id, worker_id=f"worker_{worker_id}")

            await asyncio.sleep(0.01)

            ctx = get_full_context()
            return {
                "worker_id": worker_id,
                "request_id": ctx["request_id"],
                "transaction_id": ctx["transaction_id"],
                "worker_ctx": ctx["worker_id"],
            }

        tasks = [worker(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        for res in results:
            w_id = res["worker_id"]
            self.assertEqual(res["request_id"], f"req_worker_{w_id}")
            self.assertEqual(res["transaction_id"], f"tx_worker_{w_id}")
            self.assertEqual(res["worker_ctx"], f"worker_{w_id}")


if __name__ == "__main__":
    unittest.main()
