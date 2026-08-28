"""
Unit tests for BuyerMandate data contract & lifecycle transition engine.
"""

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.mandate import BuyerMandate
from apps.api.domain.mandate_lifecycle import transition_mandate
from apps.api.domain.types import Currency, MandateStatus, Region


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestDomainMandate(unittest.TestCase):
    """Test BuyerMandate immutability, scope checks, and state transitions."""

    def setUp(self) -> None:
        self.now = _utc_now()
        self.mandate = BuyerMandate(
            buyer_id="buyer-123",
            merchant_scope=frozenset({"merchant-alpha", "merchant-beta"}),
            category_scope=frozenset({"footwear", "accessories"}),
            allowed_regions=frozenset({Region.IN}),
            maximum_amount_paise=300000,  # ₹3,000
            daily_budget_paise=500000,  # ₹5,000
            currency=Currency.INR,
            autonomous_execution=True,
            expires_at=self.now + timedelta(hours=1),
            status=MandateStatus.DRAFT,
        )

    def test_construction_and_defaults(self) -> None:
        self.assertEqual(self.mandate.buyer_id, "buyer-123")
        self.assertEqual(self.mandate.status, MandateStatus.DRAFT)
        self.assertTrue(self.mandate.authorizes_merchant("merchant-alpha"))
        self.assertFalse(self.mandate.authorizes_merchant("merchant-charlie"))

    def test_category_normalization(self) -> None:
        self.assertTrue(self.mandate.authorizes_category("Footwear"))
        self.assertTrue(self.mandate.authorizes_category("FOOTWEAR"))
        self.assertFalse(self.mandate.authorizes_category("electronics"))

    def test_amount_and_region_authorization(self) -> None:
        self.assertTrue(self.mandate.authorizes_amount(300000))
        self.assertFalse(self.mandate.authorizes_amount(300001))
        self.assertTrue(self.mandate.authorizes_region(Region.IN))
        self.assertFalse(self.mandate.authorizes_region(Region.US))

    def test_expiry_validation(self) -> None:
        with self.assertRaises(ValueError):
            BuyerMandate(
                buyer_id="b-1",
                maximum_amount_paise=100,
                daily_budget_paise=200,
                currency=Currency.INR,
                autonomous_execution=True,
                issued_at=self.now,
                expires_at=self.now - timedelta(seconds=1),
            )

    def test_budget_must_be_ge_max_amount(self) -> None:
        with self.assertRaises(ValueError):
            BuyerMandate(
                buyer_id="b-1",
                maximum_amount_paise=500000,  # ₹5,000
                daily_budget_paise=300000,  # ₹3,000 < max_amount
                currency=Currency.INR,
                autonomous_execution=True,
                expires_at=self.now + timedelta(hours=1),
            )

    def test_legal_lifecycle_transitions(self) -> None:
        # DRAFT -> ACTIVE
        active = transition_mandate(self.mandate, MandateStatus.ACTIVE)
        self.assertEqual(active.status, MandateStatus.ACTIVE)
        self.assertTrue(active.is_active())

        # ACTIVE -> SUSPENDED
        suspended = transition_mandate(active, MandateStatus.SUSPENDED)
        self.assertEqual(suspended.status, MandateStatus.SUSPENDED)
        self.assertFalse(suspended.is_active())

        # SUSPENDED -> ACTIVE
        active_again = transition_mandate(suspended, MandateStatus.ACTIVE)
        self.assertEqual(active_again.status, MandateStatus.ACTIVE)

        # ACTIVE -> REVOKED
        revoked = transition_mandate(active_again, MandateStatus.REVOKED)
        self.assertEqual(revoked.status, MandateStatus.REVOKED)
        self.assertFalse(revoked.is_active())

    def test_illegal_lifecycle_transition_raises(self) -> None:
        # DRAFT -> REVOKED is illegal (must go DRAFT -> ACTIVE first)
        with self.assertRaises(ValueError):
            transition_mandate(self.mandate, MandateStatus.REVOKED)

        # Terminal state REVOKED -> ACTIVE is illegal
        active = transition_mandate(self.mandate, MandateStatus.ACTIVE)
        revoked = transition_mandate(active, MandateStatus.REVOKED)
        with self.assertRaises(ValueError):
            transition_mandate(revoked, MandateStatus.ACTIVE)


if __name__ == "__main__":
    unittest.main()
