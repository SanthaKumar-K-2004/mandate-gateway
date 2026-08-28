"""
S02.6 — Audit Ledger Engine Unit Tests.

Tests append-only audit event recording, cryptographic hash-chain linkage,
query filtering, and chain integrity verification.
"""

import unittest

from apps.api.domain.audit import GENESIS_HASH
from apps.api.domain.audit_ledger import AuditLedger
from apps.api.domain.types import AuditEventType


class TestAuditLedger(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = AuditLedger()

    def test_initial_state(self) -> None:
        """Verify new ledger starts with GENESIS_HASH and 0 events."""
        self.assertEqual(self.ledger.head_hash, GENESIS_HASH)
        self.assertEqual(self.ledger.count(), 0)
        is_valid, err = self.ledger.verify_chain()
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_append_event_chain_linkage(self) -> None:
        """Verify events link previous_hash and update head_hash digest."""
        e1 = self.ledger.append_event(
            event_type=AuditEventType.MANDATE_CREATED,
            mandate_id="mandate_100",
            buyer_id="buyer_01",
            payload={"limit": 50000},
        )
        self.assertEqual(e1.previous_hash, GENESIS_HASH)
        self.assertNotEqual(e1.event_hash, GENESIS_HASH)
        self.assertEqual(self.ledger.head_hash, e1.event_hash)

        e2 = self.ledger.append_event(
            event_type=AuditEventType.CART_PROPOSED,
            transaction_id="tx_100",
            mandate_id="mandate_100",
            merchant_id="merchant_01",
            payload={"total_paise": 15000},
        )
        self.assertEqual(e2.previous_hash, e1.event_hash)
        self.assertEqual(self.ledger.head_hash, e2.event_hash)
        self.assertEqual(self.ledger.count(), 2)

    def test_verify_chain_success(self) -> None:
        """Verify uncorrupted multi-event chain passes verify_chain()."""
        for i in range(10):
            self.ledger.append_event(
                event_type=AuditEventType.POLICY_EVALUATED,
                transaction_id=f"tx_{i}",
                mandate_id="mandate_1",
                payload={"step": i},
            )

        is_valid, err = self.ledger.verify_chain()
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_query_events_filtering(self) -> None:
        """Verify query_events filtering by transaction, mandate, merchant, and event_type."""
        self.ledger.append_event(
            event_type=AuditEventType.MANDATE_CREATED,
            mandate_id="m1",
            buyer_id="b1",
        )
        self.ledger.append_event(
            event_type=AuditEventType.CART_PROPOSED,
            transaction_id="tx1",
            mandate_id="m1",
            merchant_id="merch1",
        )
        self.ledger.append_event(
            event_type=AuditEventType.EXECUTION_AUTHORIZED,
            transaction_id="tx1",
            mandate_id="m1",
            merchant_id="merch1",
        )
        self.ledger.append_event(
            event_type=AuditEventType.CART_PROPOSED,
            transaction_id="tx2",
            mandate_id="m2",
            merchant_id="merch2",
        )

        # Filter by transaction_id
        tx1_events = self.ledger.query_events(transaction_id="tx1")
        self.assertEqual(len(tx1_events), 2)

        # Filter by event_type
        cart_events = self.ledger.query_events(event_type=AuditEventType.CART_PROPOSED)
        self.assertEqual(len(cart_events), 2)

        # Filter by merchant_id
        merch2_events = self.ledger.query_events(merchant_id="merch2")
        self.assertEqual(len(merch2_events), 1)
        self.assertEqual(merch2_events[0].transaction_id, "tx2")

        # Offset and limit
        paginated = self.ledger.query_events(
            event_type=AuditEventType.CART_PROPOSED, limit=1, offset=1
        )
        self.assertEqual(len(paginated), 1)
        self.assertEqual(paginated[0].transaction_id, "tx2")

    def test_get_latest_event_for_transaction(self) -> None:
        """Verify fetching most recent event for a given transaction."""
        self.ledger.append_event(
            event_type=AuditEventType.CART_PROPOSED,
            transaction_id="tx_999",
            payload={"state": 1},
        )
        self.ledger.append_event(
            event_type=AuditEventType.PAYMENT_SUCCESS,
            transaction_id="tx_999",
            payload={"state": 2},
        )

        latest = self.ledger.get_latest_event_for_transaction("tx_999")
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest.event_type, AuditEventType.PAYMENT_SUCCESS)

        none_latest = self.ledger.get_latest_event_for_transaction("nonexistent_tx")
        self.assertIsNone(none_latest)


if __name__ == "__main__":
    unittest.main()
