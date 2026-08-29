"""
M13 — Observability Concurrency Test Suite
Section M13 — Concurrency & Context Isolation Foundation
"""

import asyncio
import unittest

from apps.api.app.context import (
    clear_request_context,
    get_request_context,
    set_request_context,
)


class TestM13ObservabilityConcurrency(unittest.IsolatedAsyncioTestCase):
    """Test suite for request correlation context isolation across concurrent async tasks."""

    async def test_20_concurrent_requests_preserve_correlation_isolation(self) -> None:
        """Verify 20 concurrent async requests maintain isolated request and correlation IDs."""

        async def worker_task(task_idx: int) -> tuple[int, str, str]:
            req_id = f"req_conc_{task_idx:02d}"
            corr_id = f"corr_conc_{task_idx:02d}"
            trace_id = f"trace_conc_{task_idx:02d}"

            set_request_context(req_id, corr_id, trace_id)
            await asyncio.sleep(0.01)

            ctx = get_request_context()
            read_req_id = ctx.get("request_id") or ""
            read_corr_id = ctx.get("correlation_id") or ""

            clear_request_context()
            return task_idx, read_req_id, read_corr_id

        tasks = [asyncio.create_task(worker_task(i)) for i in range(20)]
        results = await asyncio.gather(*tasks)

        for task_idx, read_req_id, read_corr_id in results:
            expected_req = f"req_conc_{task_idx:02d}"
            expected_corr = f"corr_conc_{task_idx:02d}"
            self.assertEqual(
                read_req_id,
                expected_req,
                f"Task {task_idx} read corrupted request_id {read_req_id}",
            )
            self.assertEqual(
                read_corr_id,
                expected_corr,
                f"Task {task_idx} read corrupted correlation_id {read_corr_id}",
            )


if __name__ == "__main__":
    unittest.main()
