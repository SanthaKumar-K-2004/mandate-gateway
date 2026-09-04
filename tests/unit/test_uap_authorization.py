"""
Unit tests for UAP-Aligned Agent Authorization Layer.
"""

import unittest
from apps.api.commerce.payments import (
    AuthorizationStatus,
    UAPAuthorizationError,
    UAPAuthorizationLayer,
)


class TestUAPAuthorizationLayer(unittest.TestCase):

    def setUp(self) -> None:
        self.uap = UAPAuthorizationLayer()

    def test_issue_and_validate_token(self) -> None:
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="user_buyer_01",
            max_amount_paise=50000,
            scope_merchants=["mer_cafe_acme"],
            category_scope=["grocery", "beverage"],
        )
        self.assertTrue(policy.token.startswith("uap_tok_"))
        self.assertEqual(policy.status, AuthorizationStatus.ACTIVE)

        validated = self.uap.validate_authorization(
            token_or_id=policy.token,
            agent_id="shopping_agent_01",
            merchant_id="mer_cafe_acme",
            category="grocery",
            amount_paise=29900,
        )
        self.assertEqual(validated.authorization_id, policy.authorization_id)

    def test_revoke_authorization_fails_closed(self) -> None:
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="user_buyer_01",
            max_amount_paise=50000,
        )
        self.uap.revoke_authorization(policy.authorization_id)

        with self.assertRaises(UAPAuthorizationError) as ctx:
            self.uap.validate_authorization(
                token_or_id=policy.token,
                agent_id="shopping_agent_01",
                merchant_id="mer_cafe_acme",
                category="grocery",
                amount_paise=29900,
            )
        self.assertEqual(ctx.exception.code, "AUTHORIZATION_REVOKED")

    def test_merchant_out_of_scope(self) -> None:
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="user_buyer_01",
            scope_merchants=["mer_allowed_only"],
        )

        with self.assertRaises(UAPAuthorizationError) as ctx:
            self.uap.validate_authorization(
                token_or_id=policy.token,
                agent_id="shopping_agent_01",
                merchant_id="mer_disallowed",
                category="grocery",
                amount_paise=10000,
            )
        self.assertEqual(ctx.exception.code, "MERCHANT_OUT_OF_SCOPE")

    def test_amount_exceeds_delegation(self) -> None:
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="user_buyer_01",
            max_amount_paise=30000,  # ₹300 limit
        )

        with self.assertRaises(UAPAuthorizationError) as ctx:
            self.uap.validate_authorization(
                token_or_id=policy.token,
                agent_id="shopping_agent_01",
                merchant_id="mer_cafe_acme",
                category="grocery",
                amount_paise=40000,  # ₹400
            )
        self.assertEqual(ctx.exception.code, "AMOUNT_EXCEEDS_DELEGATION")


if __name__ == "__main__":
    unittest.main()
