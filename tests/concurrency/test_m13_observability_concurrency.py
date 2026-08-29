"""
M13 — Observability Concurrency Test Suite
Section 11 & 14 — Concurrency & Context Isolation Foundation
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import unittest

from apps.api.app.context import (
    clear_request_context,
    get_request_context,
    set_request_context,
)
from apps.api.app.metrics import metrics_registry
from apps.api.observability.alerting import alert_evaluator
from apps.api.observability.investigation import TransactionInvestigator


class TestM13ObservabilityConcurrency(unittest.IsolatedAsyncioTestCase):
    """Test suite for request correlation context isolation and metric thread safety under high concurrency."""

    def setUp(self) -> None:
        metrics_registry.reset()
        alert_evaluator.clear_alerts()

    async def test_50_concurrent_request_contexts_preserve_isolation(self) -> None:
        """Verify 50 concurrent async requests maintain strictly isolated request and correlation IDs."""

        async def worker_task(task_idx: int) -> tuple[int, str, str]:
            req_id = f"req_conc_{task_idx:02d}"
            corr_id = f"corr_conc_{task_idx:02d}"
            trace_id = f"trace_conc_{task_idx:02d}"

            set_request_context(req_id, corr_id, trace_id)
            await asyncio.sleep(0.005)

            ctx = get_request_context()
            read_req_id = ctx.get("request_id") or ""
            read_corr_id = ctx.get("correlation_id") or ""

            clear_request_context()
            return task_idx, read_req_id, read_corr_id

        tasks = [asyncio.create_task(worker_task(i)) for i in range(50)]
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

    def test_50_concurrent_metric_increments_exact_counts(self) -> None:
        """Verify 50 concurrent threads incrementing a counter produces exact count of 50."""

        def increment_worker() -> None:
            metrics_registry.increment_counter(
                "payments_created_total", labels={"environment": "test"}
            )

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(increment_worker) for _ in range(50)]
            for f in futures:
                f.result()

        total = metrics_registry.get_counter_value(
            "payments_created_total", labels={"environment": "test"}
        )
        self.assertEqual(total, 50)

    def test_concurrent_alert_evaluations_deduplicate(self) -> None:
        """Verify multiple simultaneous alert evaluations produce a deduplicated single active alert."""

        def alert_worker() -> None:
            alert_evaluator.evaluate_rule("audit_chain_verification_failure", 1.0, 1.0)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(alert_worker) for _ in range(20)]
            for f in futures:
                f.result()

        active = alert_evaluator.get_active_alerts()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["rule_name"], "audit_chain_verification_failure")

    def test_concurrent_transaction_investigations_read_consistency(self) -> None:
        """Verify concurrent read access to investigator produces consistent, uncorrupted reports."""
        inv = TransactionInvestigator()
        tx_id = "tx_conc_read_01"
        inv.register_transaction(
            tx_id,
            {
                "transaction_id": tx_id,
                "merchant_id": "m_conc",
                "buyer_id": "b_conc",
                "mandate_id": "man_conc",
                "amount_paise": 1000,
                "currency": "INR",
                "state": "COMMITTED",
            },
        )

        def read_worker() -> str:
            rep = inv.investigate(tx_id, requesting_merchant_id="m_conc")
            return str(rep["current_state"])

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_worker) for _ in range(20)]
            results = [f.result() for f in futures]

        for res in results:
            self.assertEqual(res, "COMMITTED")


if __name__ == "__main__":
    unittest.main()
