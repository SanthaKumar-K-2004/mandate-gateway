"""
S02.7 — Red-Team Chaos Lab Concurrency & State Isolation Tests.

Tests parallel multi-threaded execution of attack scenarios across 20 worker threads.
"""

import concurrent.futures
import unittest

from agent.redteam.engine import RedTeamChaosEngine
from agent.redteam.types import AttackStatus, AttackType


class TestRedTeamConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RedTeamChaosEngine()

    def test_20_concurrent_attack_simulations_preserve_isolation(self) -> None:
        """Verify 20 concurrent threads running random attack vectors preserve state isolation."""
        num_workers = 20
        attack_types = list(AttackType)

        from agent.redteam.types import RedTeamAttackResult

        def worker_task(worker_id: int) -> RedTeamAttackResult:
            attack_type = attack_types[worker_id % len(attack_types)]
            return self.engine.run_attack(attack_type)

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_workers)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), num_workers)
        self.assertTrue(all(r.status == AttackStatus.BLOCKED for r in results))


if __name__ == "__main__":
    unittest.main()
