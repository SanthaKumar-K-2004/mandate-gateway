"""
Unit tests for NonceRecord contract and nonce_engine (S01.9).
"""

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.nonce import (
    AuthorizationExpiredError,
    NonceAlreadyConsumedError,
    NonceRecord,
    generate_nonce,
)
from apps.api.domain.nonce_engine import assert_nonce_consumable, consume_nonce
from apps.api.domain.types import NonceState


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestDomainNonce(unittest.TestCase):
    """Test NonceRecord single-use consumption and freshness algorithms."""

    def setUp(self) -> None:
        self.now = _utc_now()
        self.nonce_val = generate_nonce()
        self.record = NonceRecord(
            nonce_value=self.nonce_val,
            transaction_id="tx-100",
            mandate_id="mandate-100",
            state=NonceState.ISSUED,
            expires_at=self.now + timedelta(minutes=5),
        )

    def test_generate_nonce_entropy(self) -> None:
        val1 = generate_nonce()
        val2 = generate_nonce()
        self.assertEqual(len(val1), 32)
        self.assertNotEqual(val1, val2)

    def test_nonce_consumable_success(self) -> None:
        assert_nonce_consumable(self.record, at=self.now)
        consumed = consume_nonce(self.record, at=self.now)
        self.assertEqual(consumed.state, NonceState.CONSUMED)
        self.assertIsNotNone(consumed.consumed_at)

    def test_nonce_already_consumed_raises(self) -> None:
        consumed = consume_nonce(self.record, at=self.now)
        with self.assertRaises(NonceAlreadyConsumedError):
            assert_nonce_consumable(consumed, at=self.now)
        with self.assertRaises(NonceAlreadyConsumedError):
            consume_nonce(consumed, at=self.now)

    def test_nonce_expired_raises(self) -> None:
        expired_at = self.now + timedelta(minutes=10)
        with self.assertRaises(AuthorizationExpiredError):
            assert_nonce_consumable(self.record, at=expired_at)
        with self.assertRaises(AuthorizationExpiredError):
            consume_nonce(self.record, at=expired_at)


if __name__ == "__main__":
    unittest.main()
