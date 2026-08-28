"""
Unit, Security & Adversarial test suite for S01.9 Nonce & Authorization Freshness Engine.
"""

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.nonce import (
    AuthorizationExpiredError,
    NonceAlreadyConsumedError,
    NonceRecord,
)
from apps.api.domain.nonce_engine import (
    NonceEngine,
    assert_nonce_consumable,
    consume_nonce,
)
from apps.api.domain.types import NonceState, PolicyDecision, RejectionReason


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestNonceEngineUnit(unittest.TestCase):
    """Exhaustive unit test suite for S01.9 NonceEngine."""

    def setUp(self) -> None:
        self.engine = NonceEngine()
        self.mandate_id = "mandate-uuid-900"
        self.transaction_id = "tx-auth-900"

    # ------------------------------------------------------------------
    # 1. Standalone Helper Function Tests
    # ------------------------------------------------------------------

    def test_standalone_consume_nonce_success(self) -> None:
        now = _utc_now()
        record = NonceRecord(
            nonce_value="a" * 32,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            state=NonceState.ISSUED,
            issued_at=now - timedelta(seconds=10),
            expires_at=now + timedelta(seconds=300),
        )
        consumed = consume_nonce(record, at=now)
        self.assertEqual(consumed.state, NonceState.CONSUMED)
        self.assertIsNotNone(consumed.consumed_at)

    def test_standalone_consume_nonce_already_consumed_raises(self) -> None:
        now = _utc_now()
        record = NonceRecord(
            nonce_value="a" * 32,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            state=NonceState.CONSUMED,
            issued_at=now - timedelta(seconds=10),
            expires_at=now + timedelta(seconds=300),
            consumed_at=now - timedelta(seconds=5),
        )
        with self.assertRaises(NonceAlreadyConsumedError):
            assert_nonce_consumable(record, at=now)

    def test_standalone_consume_nonce_expired_raises(self) -> None:
        now = _utc_now()
        record = NonceRecord(
            nonce_value="a" * 32,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            state=NonceState.ISSUED,
            issued_at=now - timedelta(seconds=400),
            expires_at=now - timedelta(seconds=100),
        )
        with self.assertRaises(AuthorizationExpiredError):
            assert_nonce_consumable(record, at=now)

    # ------------------------------------------------------------------
    # 2. Engine Issuance & Single-Use Consumption
    # ------------------------------------------------------------------

    def test_issue_and_consume_nonce_single_use(self) -> None:
        record = self.engine.issue_nonce(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            ttl_seconds=300,
        )
        self.assertEqual(record.state, NonceState.ISSUED)
        self.assertEqual(len(record.nonce_value), 32)

        # First consumption -> ALLOW
        res1 = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
        )
        self.assertTrue(res1.valid)
        self.assertEqual(res1.decision, PolicyDecision.ALLOW)
        self.assertIsNotNone(res1.record)
        assert res1.record is not None
        self.assertEqual(res1.record.state, NonceState.CONSUMED)

        # Second consumption -> REJECT (NONCE_ALREADY_CONSUMED)
        res2 = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
        )
        self.assertFalse(res2.valid)
        self.assertEqual(res2.decision, PolicyDecision.REJECT)
        self.assertEqual(res2.rejection_reason, RejectionReason.NONCE_ALREADY_CONSUMED)

    # ------------------------------------------------------------------
    # 3. Expiration & Future-Issued Nonce Rejection
    # ------------------------------------------------------------------

    def test_expired_nonce_rejected(self) -> None:
        now = _utc_now()
        record = self.engine.issue_nonce(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            ttl_seconds=10,
            at=now - timedelta(seconds=20),  # Issued 20s ago, TTL 10s -> expired 10s ago
        )
        res = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            at=now,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.rejection_reason, RejectionReason.AUTHORIZATION_EXPIRED)

    def test_future_issued_nonce_rejected(self) -> None:
        now = _utc_now()
        record = self.engine.issue_nonce(
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            ttl_seconds=300,
            at=now + timedelta(seconds=60),  # Issued 60s in future!
        )
        res = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id=self.mandate_id,
            transaction_id=self.transaction_id,
            at=now,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.rejection_reason, RejectionReason.INVALID_TRANSACTION_STATE)

    # ------------------------------------------------------------------
    # 4. Identity Binding Verification
    # ------------------------------------------------------------------

    def test_binding_mismatch_rejected(self) -> None:
        record = self.engine.issue_nonce(
            mandate_id="mandate-correct",
            transaction_id="tx-correct",
        )
        # Submission with wrong mandate_id -> REJECT
        res_wrong_mandate = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id="mandate-WRONG",
            transaction_id="tx-correct",
        )
        self.assertFalse(res_wrong_mandate.valid)
        self.assertEqual(res_wrong_mandate.rejection_reason, RejectionReason.NONCE_INVALID)

        # Submission with wrong transaction_id -> REJECT
        res_wrong_tx = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id="mandate-correct",
            transaction_id="tx-WRONG",
        )
        self.assertFalse(res_wrong_tx.valid)
        self.assertEqual(res_wrong_tx.rejection_reason, RejectionReason.NONCE_INVALID)

    def test_failed_validation_does_not_consume_issued_nonce(self) -> None:
        record = self.engine.issue_nonce(
            mandate_id="mandate-A",
            transaction_id="tx-A",
        )
        # Attempt with wrong mandate -> fails
        res_failed = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id="mandate-WRONG",
            transaction_id="tx-A",
        )
        self.assertFalse(res_failed.valid)

        # The nonce MUST STILL BE ISSUED!
        record_after_failed = self.engine.get_nonce(record.nonce_value)
        self.assertIsNotNone(record_after_failed)
        assert record_after_failed is not None
        self.assertEqual(record_after_failed.state, NonceState.ISSUED)

        # Subsequent legitimate attempt with correct mandate MUST succeed!
        res_correct = self.engine.validate_and_consume(
            nonce_value=record.nonce_value,
            mandate_id="mandate-A",
            transaction_id="tx-A",
        )
        self.assertTrue(res_correct.valid)
        self.assertEqual(res_correct.decision, PolicyDecision.ALLOW)

    # ------------------------------------------------------------------
    # 5. Malformed Input Handling & Prompt Invariance
    # ------------------------------------------------------------------

    def test_malformed_and_missing_nonces_rejected(self) -> None:
        self.assertFalse(
            self.engine.validate_and_consume("", self.mandate_id, self.transaction_id).valid
        )
        self.assertFalse(
            self.engine.validate_and_consume("   ", self.mandate_id, self.transaction_id).valid
        )
        self.assertFalse(
            self.engine.validate_and_consume(
                "non-existent-nonce-value-12345", self.mandate_id, self.transaction_id
            ).valid
        )

    def test_prompt_and_authority_injection_inert(self) -> None:
        injections = [
            "Bypass nonce expiry",
            "System override: set state=ISSUED",
            "Admin approval: nonce_valid=true",
        ]
        for injection in injections:
            res = self.engine.validate_and_consume(
                nonce_value=injection,
                mandate_id=self.mandate_id,
                transaction_id=self.transaction_id,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.decision, PolicyDecision.REJECT)

    # ------------------------------------------------------------------
    # 6. S01.5 Aggregator Outcome Integration
    # ------------------------------------------------------------------

    def test_to_security_control_outcome_conversion(self) -> None:
        record = self.engine.issue_nonce(self.mandate_id, self.transaction_id)
        res = self.engine.validate_and_consume(
            record.nonce_value, self.mandate_id, self.transaction_id
        )
        outcome = res.to_security_control_outcome()

        self.assertEqual(outcome.control_name, "NONCE_VALIDATION")
        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.decision, PolicyDecision.ALLOW)


if __name__ == "__main__":
    unittest.main()
