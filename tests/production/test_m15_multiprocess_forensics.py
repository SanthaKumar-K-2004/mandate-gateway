"""
Production tests for M15 Multi-Process Forensic Recording & Observability.
"""

import multiprocessing
import unittest

from apps.api.observability.forensics import ForensicEngine


def _child_forensic_worker(worker_id: int, return_dict: dict) -> None:
    """Independent OS worker process recording forensic events."""
    try:
        engine = ForensicEngine()
        import asyncio

        async def run() -> None:
            await engine.record_event(
                event_type=f"mp.test_event_{worker_id}",
                category="SECURITY",
                severity="INFO",
                outcome="SUCCESS",
                metadata={"worker_id": worker_id},
            )

        asyncio.run(run())
        return_dict[worker_id] = True
    except Exception as exc:
        return_dict[worker_id] = str(exc)


class TestM15MultiprocessForensics(unittest.TestCase):
    def test_multiprocess_forensic_recording(self) -> None:
        """Verify independent OS worker processes record forensic events cleanly without cross-process IPC crashes."""
        manager = multiprocessing.Manager()
        return_dict = manager.dict()

        processes = []
        for i in range(4):
            p = multiprocessing.Process(target=_child_forensic_worker, args=(i, return_dict))
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=10)

        self.assertEqual(len(return_dict), 4)
        for i in range(4):
            self.assertIs(return_dict[i], True)


if __name__ == "__main__":
    unittest.main()
