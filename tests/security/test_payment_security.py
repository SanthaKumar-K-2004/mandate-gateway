"""
Adversarial security tests for payment invariants, replay protection, and policy enforcement.
"""

import unittest
from apps.api.commerce.payments import (
    AgentPaymentPolicyEngine,
    RazorpayClient,
    UAPAuthorizationError,
    UAPAuthorizationLayer,
    X402PaymentAdapter,
    X402PaymentError,
)


class TestPaymentSecurityInvariants(unittest.TestCase):

    def setUp(self) -> None:
        self.policy_engine = AgentPaymentPolicyEngine()
        self.uap = UAPAuthorizationLayer()
        self.x402 = X402PaymentAdapter()

    def test_amount_tampering_blocked(self) -> None:
        """User delegates ₹300, agent attempts to pay ₹400 -> BLOCKED."""
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="buyer_01",
            max_amount_paise=30000,  # ₹300
        )

        with self.assertRaises(UAPAuthorizationError) as ctx:
            self.uap.validate_authorization(
                token_or_id=policy.token,
                agent_id="shopping_agent_01",
                merchant_id="mer_cafe_acme",
                category="grocery",
                amount_paise=40000,  # ₹400 tampered amount
            )
        self.assertEqual(ctx.exception.code, "AMOUNT_EXCEEDS_DELEGATION")

    def test_merchant_tampering_blocked(self) -> None:
        """User delegates scope to 'mer_cafe_acme', agent attempts 'mer_rogue' -> BLOCKED."""
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="buyer_01",
            scope_merchants=["mer_cafe_acme"],
        )

        with self.assertRaises(UAPAuthorizationError) as ctx:
            self.uap.validate_authorization(
                token_or_id=policy.token,
                agent_id="shopping_agent_01",
                merchant_id="mer_rogue",
                category="grocery",
                amount_paise=29900,
            )
        self.assertEqual(ctx.exception.code, "MERCHANT_OUT_OF_SCOPE")

    def test_agent_identity_tampering_blocked(self) -> None:
        """Token issued to 'shopping_agent_01', malicious agent 'rogue_agent' attempts use -> BLOCKED."""
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="buyer_01",
        )

        with self.assertRaises(UAPAuthorizationError) as ctx:
            self.uap.validate_authorization(
                token_or_id=policy.token,
                agent_id="rogue_agent",
                merchant_id="mer_cafe_acme",
                category="grocery",
                amount_paise=29900,
            )
        self.assertEqual(ctx.exception.code, "AGENT_MISMATCH")

    def test_revoked_token_replay_blocked(self) -> None:
        """Token is revoked by user, immediate subsequent transaction fails closed."""
        policy = self.uap.issue_authorization(
            agent_id="shopping_agent_01",
            user_id="buyer_01",
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

    def test_x402_proof_replay_blocked(self) -> None:
        """x402 proof token cannot be replayed for a second resource request."""
        body = {"amount_paise": 29900, "currency": "INR"}
        req = self.x402.parse_402_header_or_body(
            resource_url="https://api.cafeacme.local/p/resource",
            status_code=402,
            headers={},
            body=body,
        )
        proof = self.x402.generate_payment_proof(
            requirement=req,
            transaction_id="tx_sec_01",
            agent_id="shopping_agent_01",
        )
        # Settle first time -> PASS
        self.assertTrue(self.x402.verify_and_settle_proof(proof, req))

        # Replay second time -> FAIL
        with self.assertRaises(X402PaymentError) as ctx:
            self.x402.verify_and_settle_proof(proof, req)
        self.assertEqual(ctx.exception.code, "PROOF_REPLAYED")

    def test_unknown_payment_status_does_not_become_success(self) -> None:
        """Unknown status from provider MUST remain UNKNOWN and fail-closed."""
        client = RazorpayClient()
        status = client.get_payment_status("pay_unknown_99999")
        self.assertNotEqual(status.value, "SUCCESS")
        self.assertNotEqual(status.value, "CAPTURED")
        self.assertEqual(status.value, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
