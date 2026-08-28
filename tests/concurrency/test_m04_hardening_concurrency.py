"""
M04 — System Hardening 100-Worker Concurrency Test Suite.
"""

import unittest

from apps.api.domain.system_hardening import SystemHardeningEngine


class TestM04HardeningConcurrency(unittest.TestCase):
    """Concurrency stress test suite evaluating 100 parallel worker threads."""

    def setUp(self) -> None:
        self.engine = SystemHardeningEngine()

    def test_100_worker_concurrency_stress(self) -> None:
        res = self.engine.run_100_worker_concurrency_stress()
        self.assertEqual(res["workers_fired"], 100)
        self.assertEqual(res["successful_reservations"], 1)
        self.assertEqual(res["rejected_reservations"], 99)
        self.assertTrue(res["atomic_exact_once_verified"])
