"""
M04 — System Hardening Unit Test Suite.
"""

import unittest

from agent.hardening.engine import M04HardeningManager
from apps.api.domain.system_hardening import SystemHardeningEngine


class TestM04HardeningUnit(unittest.TestCase):
    """Unit test suite for M04 System Hardening Engine and Manager."""

    def setUp(self) -> None:
        self.engine = SystemHardeningEngine()
        self.manager = M04HardeningManager()

    def test_audit_state_machines(self) -> None:
        res = self.engine.audit_state_machines()
        self.assertTrue(res["step_up_states_valid"])
        self.assertTrue(res["mandate_states_valid"])
        self.assertTrue(res["transaction_states_valid"])

    def test_manager_run_audit(self) -> None:
        rep = self.manager.run_audit()
        self.assertEqual(rep.status, "COMPLETED_AND_FROZEN")
        self.assertTrue(rep.all_tests_passed)
        self.assertEqual(rep.state_machines_audited, 3)
        self.assertEqual(rep.concurrency_workers_tested, 100)
