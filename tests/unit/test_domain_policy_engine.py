"""
Unit tests for PolicyEngine deterministic evaluation (S01.5).
"""

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.budget import DailyBudget
from apps.api.domain.cart import CartItem
from apps.api.domain.cart_integrity import build_cart_with_hash
from apps.api.domain.mandate import BuyerMandate
from apps.api.domain.merchant import MerchantPolicy
from apps.api.domain.policy_engine import PolicyEngine
from apps.api.domain.types import (
    Currency,
    MandateStatus,
    McpOperation,
    PolicyDecision,
    Region,
    RejectionReason,
)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestDomainPolicyEngine(unittest.TestCase):
    """Test all 13 authorization checks in PolicyEngine deterministically."""

    def setUp(self) -> None:
        self.now = _utc_now()
        self.mandate = BuyerMandate(
            buyer_id="buyer-100",
            merchant_scope=frozenset({"merchant-alpha"}),
            category_scope=frozenset({"footwear", "accessories"}),
            allowed_regions=frozenset({Region.IN}),
            maximum_amount_paise=300000,  # ₹3,000
            daily_budget_paise=500000,  # ₹5,000
            currency=Currency.INR,
            autonomous_execution=True,
            expires_at=self.now + timedelta(hours=2),
            status=MandateStatus.ACTIVE,
        )

        self.merchant_policy = MerchantPolicy(
            merchant_id="merchant-alpha",
            policy_version=1,
            ai_commerce_enabled=True,
            currency=Currency.INR,
            allowed_categories=frozenset({"footwear", "accessories"}),
            autonomous_purchase_limit_paise=500000,  # ₹5,000
            step_up_threshold_paise=300000,  # ₹3,000
            max_step_up_percent=10,
            allowed_regions=frozenset({Region.IN}),
            allowed_operations=frozenset(
                {
                    McpOperation.CREATE_ORDER,
                    McpOperation.CREATE_PAYMENT_LINK,
                    McpOperation.FETCH_PAYMENT,
                }
            ),
            blocked_operations=frozenset(
                {
                    McpOperation.PAYOUT,
                    McpOperation.SETTLEMENT,
                    McpOperation.BANK_TRANSFER,
                }
            ),
        )

        self.item = CartItem(
            product_id="prod-1",
            merchant_id="merchant-alpha",
            name="Running Shoes",
            category="footwear",
            quantity=1,
            unit_price_paise=250000,  # ₹2,500 <= mandate cap ₹3,000
            currency=Currency.INR,
        )

        self.cart = build_cart_with_hash(
            merchant_id="merchant-alpha",
            mandate_id=self.mandate.mandate_id,
            currency=Currency.INR,
            items=(self.item,),
            total_paise=250000,
        )

        self.budget = DailyBudget(
            mandate_id=self.mandate.mandate_id,
            currency=Currency.INR,
            date_utc="2026-08-26",
            daily_limit_paise=500000,
            spent_paise=0,
            reserved_paise=0,
        )

    def test_happy_path_allow(self) -> None:
        result = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=self.cart,
            budget=self.budget,
            at=self.now,
        )
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertTrue(result.is_allowed)
        self.assertIsNone(result.rejection_reason)
        self.assertIn("MERCHANT_AI_COMMERCE_ENABLED", result.trace.checks_passed)

    def test_merchant_ai_commerce_disabled_rejects(self) -> None:
        disabled_policy = self.merchant_policy.model_copy(update={"ai_commerce_enabled": False})
        result = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=disabled_policy,
            cart=self.cart,
            at=self.now,
        )
        self.assertEqual(result.decision, PolicyDecision.REJECT)
        self.assertEqual(result.rejection_reason, RejectionReason.AI_COMMERCE_DISABLED)

    def test_blocked_mcp_operation_rejects(self) -> None:
        result = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=self.cart,
            operation=McpOperation.PAYOUT,  # Blocked operation!
            at=self.now,
        )
        self.assertEqual(result.decision, PolicyDecision.REJECT)
        self.assertEqual(result.rejection_reason, RejectionReason.OPERATION_NOT_ALLOWED)

    def test_expired_mandate_rejects(self) -> None:
        result = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=self.cart,
            at=self.now + timedelta(hours=3),  # past expiry
        )
        self.assertEqual(result.decision, PolicyDecision.REJECT)
        self.assertEqual(result.rejection_reason, RejectionReason.MANDATE_EXPIRED)

    def test_merchant_not_in_scope_rejects(self) -> None:
        other_item = self.item.model_copy(update={"merchant_id": "merchant-charlie"})
        valid_other_cart = build_cart_with_hash(
            merchant_id="merchant-charlie",
            mandate_id=self.mandate.mandate_id,
            currency=Currency.INR,
            items=(other_item,),
            total_paise=250000,
        )
        result = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=valid_other_cart,
            at=self.now,
        )
        self.assertEqual(result.decision, PolicyDecision.REJECT)
        self.assertEqual(result.rejection_reason, RejectionReason.MERCHANT_NOT_IN_SCOPE)

    def test_step_up_required(self) -> None:
        # Proposed ₹3,120 (+4% over mandate cap ₹3,000) -> Zone B -> STEP_UP_REQUIRED
        expensive_item = self.item.model_copy(update={"unit_price_paise": 312000})
        expensive_cart = build_cart_with_hash(
            merchant_id="merchant-alpha",
            mandate_id=self.mandate.mandate_id,
            currency=Currency.INR,
            items=(expensive_item,),
            total_paise=312000,
        )
        result = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=expensive_cart,
            budget=self.budget,
            at=self.now,
        )
        self.assertEqual(result.decision, PolicyDecision.STEP_UP_REQUIRED)
        self.assertIsNotNone(result.step_up_diff)
        assert result.step_up_diff is not None
        self.assertEqual(result.step_up_diff.delta_paise, 12000)  # ₹120

    def test_hard_reject_exceeding_step_up_threshold(self) -> None:
        # Proposed ₹3,500 (+16.6% over mandate cap ₹3,000 > max 10%) -> Zone C -> REJECT
        very_expensive_item = self.item.model_copy(update={"unit_price_paise": 350000})
        very_expensive_cart = build_cart_with_hash(
            merchant_id="merchant-alpha",
            mandate_id=self.mandate.mandate_id,
            currency=Currency.INR,
            items=(very_expensive_item,),
            total_paise=350000,
        )
        result = PolicyEngine.evaluate(
            mandate=self.mandate,
            merchant_policy=self.merchant_policy,
            cart=very_expensive_cart,
            budget=self.budget,
            at=self.now,
        )
        self.assertEqual(result.decision, PolicyDecision.REJECT)
        self.assertEqual(result.rejection_reason, RejectionReason.EXCEEDS_STEP_UP_HARD_LIMIT)


if __name__ == "__main__":
    unittest.main()
