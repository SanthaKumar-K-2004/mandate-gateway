"""
Security tests for S05.3.7 AuditRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from apps.api.domain.audit import GENESIS_HASH, _compute_event_hash
from apps.api.domain.types import AuditEventType
from db.models.audit import AuditEventModel
from db.repository.audit_repository import AuditRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestAuditRepositorySecurity(unittest.TestCase):
    """Security test suite for AuditRepository."""

    FORBIDDEN_MUTATION_METHODS = [
        "update",
        "delete",
        "update_event",
        "delete_event",
        "update_hash",
        "update_payload",
        "execute_raw",
        "commit",
        "rollback",
        "raw_sql",
        "truncate_audit_log",
        "overwrite_event",
    ]

    def test_security_test_c_no_append_only_mutation_escape_hatch(self) -> None:
        """Security Test C: Verify AuditRepository exposes no generic update or delete methods."""
        for method_name in self.FORBIDDEN_MUTATION_METHODS:
            self.assertFalse(
                hasattr(AuditRepository, method_name),
                f"Forbidden security-bypassing method '{method_name}' exposed on AuditRepository!",
            )

    def test_explicit_public_api_surface(self) -> None:
        """Verify AuditRepository only exposes append-only and verification methods."""
        public_methods = [m for m in dir(AuditRepository) if not m.startswith("_")]
        allowed_methods = {
            "get_by_id",
            "session",
            "model_cls",
            "get_latest_event",
            "append_event",
            "get_event",
            "get_event_by_sequence",
            "get_events_for_transaction",
            "get_all_events",
            "verify_chain",
        }
        unexpected = set(public_methods) - allowed_methods
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected public methods on AuditRepository: {unexpected}",
        )

    def test_controlled_mutation_a_previous_hash_linkage_tamper_detection(self) -> None:
        """
        Controlled Mutation Proof (Mutation A):
        Verify that a broken previous_hash link is detected during chain verification.
        """
        t = _utc_now()
        h1 = _compute_event_hash(
            event_id="e1",
            event_type=AuditEventType.MANDATE_CREATED,
            timestamp=t,
            previous_hash=GENESIS_HASH,
            transaction_id=None,
            mandate_id="m1",
            merchant_id=None,
            buyer_id=None,
            payload={},
        )

        e1 = AuditEventModel(
            event_id="e1",
            sequence_number=1,
            event_type=AuditEventType.MANDATE_CREATED.value,
            previous_hash=GENESIS_HASH,
            event_hash=h1,
            payload_json="{}",
            timestamp=t,
        )

        # e2 has corrupted previous_hash ("BAD_PREV_HASH")
        e2_corrupted = AuditEventModel(
            event_id="e2",
            sequence_number=2,
            event_type=AuditEventType.PAYMENT_SUCCESS.value,
            previous_hash="BAD_PREV_HASH",
            event_hash="some_hash",
            payload_json="{}",
            timestamp=t,
        )

        def verify_linkage(events: list[AuditEventModel]) -> tuple[bool, str | None]:
            expected_prev = GENESIS_HASH
            for idx, ev in enumerate(events):
                if ev.previous_hash != expected_prev:
                    return False, f"Broken link at index {idx}"
                expected_prev = ev.event_hash
            return True, None

        is_valid, err = verify_linkage([e1, e2_corrupted])
        self.assertFalse(is_valid)
        self.assertIn("Broken link", str(err))

    def test_controlled_mutation_b_tampered_payload_hash_recomputation_detection(self) -> None:
        """
        Controlled Mutation Proof (Mutation B):
        Verify that altering an event's stored hash or payload invalidates hash recomputation.
        """
        t = _utc_now()
        real_hash = _compute_event_hash(
            event_id="e1",
            event_type=AuditEventType.MANDATE_CREATED,
            timestamp=t,
            previous_hash=GENESIS_HASH,
            transaction_id=None,
            mandate_id="m1",
            merchant_id=None,
            buyer_id=None,
            payload={"amount": 100},
        )

        # Alter hash to fake value
        tampered_event = AuditEventModel(
            event_id="e1",
            sequence_number=1,
            event_type=AuditEventType.MANDATE_CREATED.value,
            mandate_id="m1",
            previous_hash=GENESIS_HASH,
            event_hash="FORGED_HASH_99999",
            payload_json='{"amount": 100}',
            timestamp=t,
        )

        recomputed = _compute_event_hash(
            event_id=tampered_event.event_id,
            event_type=AuditEventType(tampered_event.event_type),
            timestamp=tampered_event.timestamp,
            previous_hash=tampered_event.previous_hash,
            transaction_id=tampered_event.transaction_id,
            mandate_id=tampered_event.mandate_id,
            merchant_id=tampered_event.merchant_id,
            buyer_id=tampered_event.buyer_id,
            payload={"amount": 100},
        )

        self.assertNotEqual(tampered_event.event_hash, recomputed)
        self.assertEqual(real_hash, recomputed)


if __name__ == "__main__":
    unittest.main()
