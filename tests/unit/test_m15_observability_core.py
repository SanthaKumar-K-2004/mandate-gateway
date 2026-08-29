"""
Unit tests for M15 Observability Core & Context Propagation.
"""

import unittest

from apps.api.app.context import (
    clear_request_context,
    get_full_context,
    set_request_context,
    set_transaction_context,
    validate_and_sanitize_request_id,
)


class TestM15ObservabilityCoreUnit(unittest.TestCase):
    def setUp(self) -> None:
        clear_request_context()

    def tearDown(self) -> None:
        clear_request_context()

    def test_request_id_sanitization_and_validation(self) -> None:
        """Verify valid request IDs are preserved and invalid/injection IDs generate UUIDv4 fallback."""
        self.assertTrue(validate_and_sanitize_request_id("req_12345").startswith("req_12345"))

        # Test fallback on invalid characters / injection payloads
        bad_id = "<script>alert(1)</script>"
        clean = validate_and_sanitize_request_id(bad_id)
        self.assertTrue(clean.startswith("req_"))
        self.assertNotIn("<script>", clean)

        # Test fallback on oversized string
        oversized = "a" * 200
        clean_over = validate_and_sanitize_request_id(oversized)
        self.assertTrue(clean_over.startswith("req_"))

    def test_context_set_and_clear(self) -> None:
        """Verify request and transaction context variables set and clear cleanly."""
        set_request_context("req_test_01", "corr_test_01", "trace_test_01")
        set_transaction_context(
            transaction_id="tx_100",
            merchant_id="mer_100",
            audit_event_id="aud_100",
            receipt_id="rcp_100",
            webhook_event_id="wh_100",
            worker_id="worker_01",
        )

        ctx = get_full_context()
        self.assertEqual(ctx["request_id"], "req_test_01")
        self.assertEqual(ctx["correlation_id"], "corr_test_01")
        self.assertEqual(ctx["transaction_id"], "tx_100")
        self.assertEqual(ctx["audit_event_id"], "aud_100")
        self.assertEqual(ctx["receipt_id"], "rcp_100")
        self.assertEqual(ctx["webhook_event_id"], "wh_100")
        self.assertEqual(ctx["worker_id"], "worker_01")

        clear_request_context()
        cleared_ctx = get_full_context()
        self.assertIsNone(cleared_ctx["request_id"])
        self.assertIsNone(cleared_ctx["transaction_id"])


if __name__ == "__main__":
    unittest.main()
