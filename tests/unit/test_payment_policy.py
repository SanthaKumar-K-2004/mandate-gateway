"""
Unit tests for Agent Payment Policy Engine and Risk Classifier.
"""

import unittest
from apps.api.commerce.payments import (
    AgentPaymentPolicyEngine,
    PolicyEvaluationContext,
    RiskLevel,
)


class TestPaymentPolicyEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.engine = AgentPaymentPolicyEngine()

    def test_default_policy_evaluation_success(self) -> None:
        ctx = PolicyEvaluationContext(
            agent_id="shopping_agent_01",
            request_id="req_001",
            user_id="user_01",
            merchant_id="mer_cafe_acme",
            merchant_name="Cafe Acme",
            category="grocery",
            currency="INR",
            amount_paise=29900,  # ₹299
            provider="razorpay_test",
            is_product_verified=True,
            has_human_confirmation=True,
        )
        res = self.engine.evaluate(ctx)
        self.assertTrue(res.allowed)
        self.assertEqual(res.risk_level, RiskLevel.LOW)

    def test_unverified_product_block(self) -> None:
        ctx = PolicyEvaluationContext(
            agent_id="shopping_agent_01",
            request_id="req_002",
            user_id="user_01",
            merchant_id="mer_cafe_acme",
            merchant_name="Cafe Acme",
            category="grocery",
            currency="INR",
            amount_paise=29900,
            provider="razorpay_test",
            is_product_verified=False,  # Unverified
            has_human_confirmation=True,
        )
        res = self.engine.evaluate(ctx)
        self.assertFalse(res.allowed)
        self.assertEqual(res.block_code, "UNVERIFIED_PRODUCT")

    def test_missing_human_confirmation_block(self) -> None:
        ctx = PolicyEvaluationContext(
            agent_id="shopping_agent_01",
            request_id="req_003",
            user_id="user_01",
            merchant_id="mer_cafe_acme",
            merchant_name="Cafe Acme",
            category="grocery",
            currency="INR",
            amount_paise=29900,
            provider="razorpay_test",
            is_product_verified=True,
            has_human_confirmation=False,  # Missing confirmation
        )
        res = self.engine.evaluate(ctx)
        self.assertFalse(res.allowed)
        self.assertEqual(res.block_code, "HUMAN_CONFIRMATION_REQUIRED")

    def test_per_transaction_limit_exceeded(self) -> None:
        ctx = PolicyEvaluationContext(
            agent_id="shopping_agent_01",
            request_id="req_004",
            user_id="user_01",
            merchant_id="mer_cafe_acme",
            merchant_name="Cafe Acme",
            category="grocery",
            currency="INR",
            amount_paise=160000,  # ₹1,600 > ₹1,500 limit
            provider="razorpay_test",
            is_product_verified=True,
            has_human_confirmation=True,
        )
        res = self.engine.evaluate(ctx)
        self.assertFalse(res.allowed)
        self.assertEqual(res.block_code, "PER_TRANSACTION_LIMIT_EXCEEDED")

    def test_daily_limit_cumulative_tracking(self) -> None:
        # Spend ₹400 first
        self.engine.record_spending("shopping_agent_01", 40000)

        # Attempt another ₹400 (Total ₹800 < ₹5,000 limit) -> PASS
        ctx1 = PolicyEvaluationContext(
            agent_id="shopping_agent_01",
            request_id="req_005",
            user_id="user_01",
            merchant_id="mer_cafe_acme",
            merchant_name="Cafe Acme",
            category="grocery",
            currency="INR",
            amount_paise=40000,
            provider="razorpay_test",
            is_product_verified=True,
            has_human_confirmation=True,
        )
        self.assertTrue(self.engine.evaluate(ctx1).allowed)

        # Record second spend (Total now ₹800)
        self.engine.record_spending("shopping_agent_01", 40000)

        # Record spend up to ₹4,800
        self.engine.record_spending("shopping_agent_01", 400000)

        # Attempt another ₹300 (Total ₹5,100 > ₹5,000 limit) -> FAIL
        ctx2 = PolicyEvaluationContext(
            agent_id="shopping_agent_01",
            request_id="req_006",
            user_id="user_01",
            merchant_id="mer_cafe_acme",
            merchant_name="Cafe Acme",
            category="grocery",
            currency="INR",
            amount_paise=30000,
            provider="razorpay_test",
            is_product_verified=True,
            has_human_confirmation=True,
        )
        res = self.engine.evaluate(ctx2)
        self.assertFalse(res.allowed)
        self.assertEqual(res.block_code, "DAILY_LIMIT_EXCEEDED")

    def test_disallowed_currency(self) -> None:
        ctx = PolicyEvaluationContext(
            agent_id="shopping_agent_01",
            request_id="req_007",
            user_id="user_01",
            merchant_id="mer_cafe_acme",
            merchant_name="Cafe Acme",
            category="grocery",
            currency="USD",  # Disallowed
            amount_paise=29900,
            provider="razorpay_test",
            is_product_verified=True,
            has_human_confirmation=True,
        )
        res = self.engine.evaluate(ctx)
        self.assertFalse(res.allowed)
        self.assertEqual(res.block_code, "DISALLOWED_CURRENCY")


if __name__ == "__main__":
    unittest.main()
