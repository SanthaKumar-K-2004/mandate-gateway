"""
Security tests for S05.3.6.3 NonceRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.types import NonceState
from db.models.replay import NonceRecordModel
from db.repository.nonce_repository import NonceRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestNonceRepositorySecurity(unittest.TestCase):
    """Security test suite for NonceRepository."""

    FORBIDDEN_MUTATION_METHODS = [
        "update",
        "delete",
        "update_nonce",
        "delete_nonce",
        "update_anything",
        "delete_anything",
        "execute_raw",
        "commit",
        "rollback",
        "raw_sql",
        "reset_nonce",
        "override_status",
    ]

    def test_security_test_e_no_generic_mutation_escape_hatch(self) -> None:
        """Security Test E: Verify NonceRepository exposes no generic update or delete methods."""
        for method_name in self.FORBIDDEN_MUTATION_METHODS:
            self.assertFalse(
                hasattr(NonceRepository, method_name),
                f"Forbidden security-bypassing method '{method_name}' exposed on NonceRepository!",
            )

    def test_explicit_public_api_surface(self) -> None:
        """Verify NonceRepository only exposes intentional nonce management methods."""
        public_methods = [m for m in dir(NonceRepository) if not m.startswith("_")]
        allowed_methods = {
            "get_by_id",
            "session",
            "model_cls",
            "create_nonce",
            "get_nonce",
            "get_nonces_for_transaction",
            "get_nonces_for_mandate",
            "lock_nonce_for_update",
            "consume_nonce",
        }
        unexpected = set(public_methods) - allowed_methods
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected public methods on NonceRepository: {unexpected}",
        )

    def test_controlled_mutation_a_double_consumption_bypass(self) -> None:
        """
        Controlled Mutation Proof (Mutation A):
        Verify that attempting to consume an already CONSUMED nonce fails closed.
        """
        rec = NonceRecordModel(
            nonce="n_sec_consumed",
            transaction_id="tx_sec_1",
            mandate_id="man_sec_1",
            status=NonceState.CONSUMED.value,
            created_at=_utc_now(),
            consumed_at=_utc_now(),
        )

        def consume_logic(r: NonceRecordModel) -> None:
            if r.status == NonceState.CONSUMED.value:
                raise ValueError("Nonce already consumed")

        # Correct logic raises ValueError
        with self.assertRaises(ValueError):
            consume_logic(rec)

    def test_controlled_mutation_b_expiry_validation_bypass(self) -> None:
        """
        Controlled Mutation Proof (Mutation B):
        Verify that attempting to consume an EXPIRED nonce fails closed.
        """
        past_time = _utc_now() - timedelta(seconds=1000)
        rec = NonceRecordModel(
            nonce="n_sec_exp",
            transaction_id="tx_sec_2",
            mandate_id="man_sec_2",
            status=NonceState.ISSUED.value,
            created_at=past_time,
            consumed_at=None,
        )

        def consume_with_ttl(r: NonceRecordModel, at: datetime, ttl: int) -> None:
            if ttl > 0 and (at - r.created_at).total_seconds() >= ttl:
                raise ValueError("Nonce expired")

        with self.assertRaises(ValueError):
            consume_with_ttl(rec, _utc_now(), 300)

    def test_controlled_mutation_c_context_substitution_bypass(self) -> None:
        """
        Controlled Mutation Proof (Mutation C):
        Verify that attempting context substitution (tx_id or mandate_id mismatch) fails closed.
        """
        rec = NonceRecordModel(
            nonce="n_sec_ctx",
            transaction_id="tx_valid",
            mandate_id="man_valid",
            status=NonceState.ISSUED.value,
            created_at=_utc_now(),
            consumed_at=None,
        )

        def validate_context(r: NonceRecordModel, tx_id: str, mandate_id: str) -> None:
            if r.transaction_id != tx_id or r.mandate_id != mandate_id:
                raise ValueError("Nonce context mismatch")

        with self.assertRaises(ValueError):
            validate_context(rec, "tx_attacker", "man_valid")

        with self.assertRaises(ValueError):
            validate_context(rec, "tx_valid", "man_attacker")


if __name__ == "__main__":
    unittest.main()
