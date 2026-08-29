"""
Security tests for M15 Forensic Integrity & Telemetry Protection.
"""

import unittest

from apps.api.observability.forensics import forensic_engine


class TestM15ObservabilitySecurity(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        forensic_engine.clear()

    def tearDown(self) -> None:
        forensic_engine.clear()

    async def test_forensic_event_secret_redaction_and_hash_integrity(self) -> None:
        """Verify forensic event payload redacts secrets and generates SHA-256 hash signature."""
        evt = await forensic_engine.record_event(
            event_type="security.test_event",
            category="SECURITY",
            severity="HIGH",
            outcome="DENIED",
            actor_principal_id="cred_test_sec",
            merchant_id="mer_sec",
            metadata={"secret_key": "rzp_live_secret_key_12345", "public_id": "pub_100"},
        )

        self.assertNotIn("rzp_live_secret_key_12345", evt.metadata_json)
        self.assertIn("[REDACTED]", evt.metadata_json)
        self.assertIn("pub_100", evt.metadata_json)
        self.assertEqual(len(evt.hash_signature), 64)


if __name__ == "__main__":
    unittest.main()
