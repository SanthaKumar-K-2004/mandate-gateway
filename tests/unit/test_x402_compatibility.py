"""
Unit tests for x402 HTTP Payment Compatibility Layer.
"""

import unittest
from apps.api.commerce.payments import (
    X402PaymentAdapter,
    X402PaymentError,
)


class TestX402Compatibility(unittest.TestCase):

    def setUp(self) -> None:
        self.adapter = X402PaymentAdapter()

    def test_parse_valid_402_body(self) -> None:
        body = {
            "amount_paise": 29900,
            "currency": "INR",
            "recipient_address": "mer_cafe_acme",
            "network": "razorpay_test",
            "ttl_seconds": 300,
        }
        req = self.adapter.parse_402_header_or_body(
            resource_url="https://api.cafeacme.local/resource/digital-item",
            status_code=402,
            headers={},
            body=body,
        )
        self.assertEqual(req.amount_paise, 29900)
        self.assertEqual(req.currency, "INR")
        self.assertEqual(req.recipient_address, "mer_cafe_acme")
        self.assertTrue(bool(req.requirement_hash))

    def test_generate_and_settle_proof(self) -> None:
        body = {"amount_paise": 15000, "currency": "INR"}
        req = self.adapter.parse_402_header_or_body(
            resource_url="https://api.cafeacme.local/resource/coffee-vouchers",
            status_code=402,
            headers={},
            body=body,
        )

        proof = self.adapter.generate_payment_proof(
            requirement=req,
            transaction_id="tx_x402_101",
            agent_id="shopping_agent_01",
        )
        self.assertTrue(proof.proof_token.startswith("x402_proof_"))

        settled = self.adapter.verify_and_settle_proof(proof, req)
        self.assertTrue(settled)

    def test_proof_replay_attack_blocked(self) -> None:
        body = {"amount_paise": 15000, "currency": "INR"}
        req = self.adapter.parse_402_header_or_body(
            resource_url="https://api.cafeacme.local/resource/coffee-vouchers",
            status_code=402,
            headers={},
            body=body,
        )

        proof = self.adapter.generate_payment_proof(
            requirement=req,
            transaction_id="tx_x402_102",
            agent_id="shopping_agent_01",
        )
        # Settle once
        self.adapter.verify_and_settle_proof(proof, req)

        # Attempt replay -> MUST FAIL
        with self.assertRaises(X402PaymentError) as ctx:
            self.adapter.verify_and_settle_proof(proof, req)
        self.assertEqual(ctx.exception.code, "PROOF_REPLAYED")


if __name__ == "__main__":
    unittest.main()
