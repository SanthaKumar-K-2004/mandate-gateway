"""
Unit tests for Step-Up evaluation service (S01.1).
"""

import unittest

from apps.api.domain.step_up import StepUpZone
from apps.api.domain.step_up_engine import classify_step_up_zone


class TestDomainStepUp(unittest.TestCase):
    """Test step-up zone classification boundaries."""

    def test_zone_a_auto_execute(self) -> None:
        res = classify_step_up_zone(
            cart_total_paise=300000,
            mandate_cap_paise=300000,
            max_step_up_percent=10,
        )
        self.assertEqual(res.zone, StepUpZone.AUTO_EXECUTE)
        self.assertIsNone(res.diff)

    def test_zone_b_step_up_required(self) -> None:
        # ₹3,120 is +4% over ₹3,000 cap (<= 10% threshold)
        res = classify_step_up_zone(
            cart_total_paise=312000,
            mandate_cap_paise=300000,
            max_step_up_percent=10,
        )
        self.assertEqual(res.zone, StepUpZone.STEP_UP_REQUIRED)
        self.assertIsNotNone(res.diff)
        assert res.diff is not None
        self.assertEqual(res.diff.approved_paise, 300000)
        self.assertEqual(res.diff.proposed_paise, 312000)
        self.assertEqual(res.diff.delta_paise, 12000)
        self.assertEqual(res.diff.delta_percent, 4.0)

    def test_zone_c_hard_reject(self) -> None:
        # ₹3,400 is +13.33% over ₹3,000 cap (> 10% threshold)
        res = classify_step_up_zone(
            cart_total_paise=340000,
            mandate_cap_paise=300000,
            max_step_up_percent=10,
        )
        self.assertEqual(res.zone, StepUpZone.HARD_REJECT)
        self.assertIn("exceeds mandate limit", res.reason)

    def test_negative_price_raises(self) -> None:
        with self.assertRaises(ValueError):
            classify_step_up_zone(cart_total_paise=-10, mandate_cap_paise=100)


if __name__ == "__main__":
    unittest.main()
