"""
Concurrency tests for M15 Forensic Engine & Multi-Task Logging.
"""

import asyncio
import unittest

from apps.api.observability.forensics import forensic_engine


class TestM15ObservabilityConcurrency(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        forensic_engine.clear()

    def tearDown(self) -> None:
        forensic_engine.clear()

    async def test_concurrent_forensic_event_recording(self) -> None:
        """Verify 100 concurrent forensic events recorded without race conditions or memory corruption."""

        async def record_task(idx: int) -> None:
            await forensic_engine.record_event(
                event_type=f"test.event_{idx}",
                category="SECURITY",
                severity="INFO",
                outcome="SUCCESS",
                metadata={"index": idx},
            )

        await asyncio.gather(*[record_task(i) for i in range(100)])
        events = forensic_engine.query_memory_events(limit=200)
        self.assertEqual(len(events), 100)


if __name__ == "__main__":
    unittest.main()
