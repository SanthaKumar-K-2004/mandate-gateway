"""
S04.4 — Integration Test Suite for Crash Consistency, Recovery & Reconciliation.

Verifies end-to-end REST router integration for GET /api/hardening/recovery-audit,
system hardening manager integration, and complete audit report structure.
"""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from agent.hardening.engine import M04HardeningManager
from apps.api.app.factory import create_app
from apps.api.domain.system_hardening import SystemHardeningEngine


class TestS044RecoveryIntegration(unittest.TestCase):
    """Integration tests for S04.4 Recovery & Reconciliation REST API and Engine."""

    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.manager = M04HardeningManager()
        self.engine = SystemHardeningEngine()

    def test_get_recovery_audit_endpoint_status(self) -> None:
        """Verify GET /api/hardening/recovery-audit returns HTTP 200 OK and valid JSON report."""
        resp = self.client.get("/api/hardening/recovery-audit")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertIn("project_context_hash", data)
        self.assertIn("crash_boundaries_audited", data)
        self.assertEqual(data["crash_boundaries_audited"], 18)
        self.assertTrue(data["nonce_recovery_integrity_valid"])
        self.assertTrue(data["stepup_recovery_integrity_valid"])
        self.assertTrue(data["audit_receipt_consistency_valid"])
        self.assertTrue(data["idempotency_after_restart_valid"])
        self.assertEqual(data["status"], "COMPLETED_AND_FROZEN")

    def test_manager_run_recovery_audit(self) -> None:
        """Verify M04HardeningManager.run_recovery_audit() returns RecoveryAuditReport DTO."""
        rep = self.manager.run_recovery_audit()
        self.assertEqual(rep.crash_boundaries_audited, 18)
        self.assertEqual(rep.status, "COMPLETED_AND_FROZEN")
        self.assertTrue(rep.fail_closed_verified)

    def test_engine_run_crash_recovery_audit(self) -> None:
        """Verify SystemHardeningEngine.run_crash_recovery_audit() returns clean report."""
        rep = self.engine.run_crash_recovery_audit()
        self.assertEqual(
            rep.project_context_hash,
            "2b62d52aa707bc9bb5df60d93b04f60933562e69af8068c46cc3b6cdc2eb670a",
        )
        self.assertTrue(rep.nonce_recovery_integrity_valid)


if __name__ == "__main__":
    unittest.main()
