"""
Integration tests for M15 Incident Classification & Anomaly Detection.
"""

import unittest

from apps.api.observability.incident_engine import incident_engine


class TestM15IncidentDetectionIntegration(unittest.TestCase):
    def setUp(self) -> None:
        incident_engine.clear()

    def tearDown(self) -> None:
        incident_engine.clear()

    def test_auth_abuse_detection_threshold(self) -> None:
        """Verify 5 failed auth attempts trigger AUTH_ABUSE_DETECTED security incident."""
        fp = "fp_test_auth_burst_123"
        for _ in range(4):
            res = incident_engine.record_auth_failure(fp, "mer_test")
            self.assertIsNone(res)

        inc = incident_engine.record_auth_failure(fp, "mer_test")
        self.assertIsNotNone(inc)
        assert inc is not None
        self.assertEqual(inc.rule_id, "AUTH_ABUSE_DETECTED")
        self.assertEqual(inc.classification, "SECURITY")
        self.assertEqual(inc.severity, "HIGH")

    def test_tenant_probing_detection(self) -> None:
        """Verify cross-tenant probing immediately raises CRITICAL SECURITY incident."""
        inc = incident_engine.record_tenant_isolation_violation("mer_attacker", "mer_target")
        self.assertEqual(inc.rule_id, "TENANT_PROBING_DETECTED")
        self.assertEqual(inc.classification, "SECURITY")
        self.assertEqual(inc.severity, "CRITICAL")
        self.assertEqual(inc.merchant_id, "mer_attacker")


if __name__ == "__main__":
    unittest.main()
