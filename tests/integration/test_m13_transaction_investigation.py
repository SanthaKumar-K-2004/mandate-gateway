"""
M13 — Integration Test Suite for Operational Transaction Investigation
Section 14 — Test Architecture
"""

import unittest

from apps.api.observability.investigation import TransactionInvestigator


class TestM13TransactionInvestigation(unittest.TestCase):
    """Integration test suite for operational transaction investigation endpoint capability."""

    def setUp(self) -> None:
        self.inv = TransactionInvestigator()

    def test_full_transaction_investigation_timeline(self) -> None:
        """Verify investigator constructs a complete, coherent chronological timeline."""
        tx_id = "tx_investigate_01"
        self.inv.register_transaction(
            tx_id,
            {
                "transaction_id": tx_id,
                "merchant_id": "merch_acme",
                "buyer_id": "buyer_101",
                "mandate_id": "mandate_555",
                "amount_paise": 25000,
                "currency": "INR",
                "state": "COMMITTED",
                "idempotency_key": "idemp_inv_01",
                "created_at": "2026-08-29T10:00:00Z",
            },
        )
        self.inv.record_execution_attempt(
            tx_id,
            {
                "status": "claimed",
                "timestamp": "2026-08-29T10:00:01Z",
                "detail": "Claimed execution lock",
                "context": {"attempt": 1, "secret_token": "tok_sec_123"},
            },
        )
        self.inv.record_receipt(
            tx_id,
            {
                "generated_at": "2026-08-29T10:00:02Z",
                "context": {"receipt_id": "rec_01", "signature": "sig_ed25519_abc"},
            },
        )
        self.inv.record_outbox_event(
            tx_id,
            {
                "event_id": "evt_outbox_01",
                "status": "published",
                "timestamp": "2026-08-29T10:00:03Z",
                "context": {"topic": "payment.events"},
            },
        )

        report = self.inv.investigate(tx_id, requesting_merchant_id="merch_acme")
        self.assertEqual(report["transaction_id"], tx_id)
        self.assertEqual(report["merchant_id"], "merch_acme")
        self.assertEqual(report["current_state"], "COMMITTED")
        self.assertTrue(report["has_receipt"])
        self.assertTrue(report["has_outbox_event"])
        self.assertGreaterEqual(len(report["timeline"]), 4)

        # Verify sensitive redaction (S03)
        formatted_str = str(report)
        self.assertNotIn("tok_sec_123", formatted_str)
        self.assertNotIn("sig_ed25519_abc", formatted_str)
        self.assertIn("[REDACTED]", formatted_str)

    def test_merchant_isolation_boundary_enforcement(self) -> None:
        """Verify querying another merchant's transaction fails closed with PermissionError (S02)."""
        tx_id = "tx_investigate_02"
        self.inv.register_transaction(
            tx_id,
            {
                "transaction_id": tx_id,
                "merchant_id": "merch_acme",
                "buyer_id": "buyer_101",
                "mandate_id": "mandate_555",
                "state": "COMMITTED",
            },
        )

        # Same merchant succeeds
        report = self.inv.investigate(tx_id, requesting_merchant_id="merch_acme")
        self.assertEqual(report["merchant_id"], "merch_acme")

        # Different merchant raises PermissionError
        with self.assertRaises(PermissionError):
            self.inv.investigate(tx_id, requesting_merchant_id="merch_evil_corp")

    def test_unknown_transaction_handling_without_inventing_history(self) -> None:
        """Verify non-existent transaction raises KeyError or explicit unknown representation."""
        with self.assertRaises(KeyError):
            self.inv.investigate("tx_non_existent")


if __name__ == "__main__":
    unittest.main()
