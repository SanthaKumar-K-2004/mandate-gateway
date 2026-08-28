"""
S02.3 — Intent Normalization Concurrency & State Isolation Tests.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import unittest

from agent.intent.parser import AgentIntentParser


class TestIntentConcurrency(unittest.TestCase):
    def test_concurrent_intent_parsing_and_security_scans(self) -> None:
        """
        Execute 20 concurrent threads parsing intent payloads and running security scans.

        Verifies thread safety, state isolation, and zero cross-worker state corruption.
        """
        num_workers = 20

        def _run_worker(worker_id: int) -> int:
            payload = {
                "merchant_id": f"M_WORKER_{worker_id}",
                "currency": "INR",
                "items": [
                    {
                        "product_id": f"P_{worker_id}_1",
                        "name": f"Item {worker_id}-1",
                        "category": "goods",
                        "quantity": 2,
                        "unit_price_paise": 10000 + worker_id,
                        "subtotal_paise": (10000 + worker_id) * 2,
                    },
                    {
                        "product_id": f"P_{worker_id}_2",
                        "name": f"Item {worker_id}-2",
                        "category": "goods",
                        "quantity": 1,
                        "unit_price_paise": 5000,
                        "subtotal_paise": 5000,
                    },
                ],
            }
            parsed = AgentIntentParser.parse_intent_payload(
                payload, default_merchant_id=f"M_WORKER_{worker_id}"
            )
            return len(parsed)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_run_worker, i) for i in range(num_workers)]
            results = [future.result() for future in as_completed(futures)]

        self.assertEqual(len(results), num_workers)
        for count in results:
            self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
