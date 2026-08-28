"""
Security test suite for S01.11 Payment Execution Boundary & SecurityToolProxy.
"""

import unittest

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter, RazorpayHttpAdapter
from apps.api.config.types import SecretString
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.tool_proxy import SecurityToolProxy
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import Currency, PolicyDecision, TransactionState


class TestExecutionSecurity(unittest.TestCase):
    """Exhaustive security test suite for S01.11 execution boundary."""

    def setUp(self) -> None:
        self.mock_adapter = MockRazorpayAdapter()
        self.service = PaymentExecutionService(self.mock_adapter)
        self.proxy = SecurityToolProxy(self.service)

        self.transaction_id = "tx-sec-100"
        self.transaction = Transaction(
            transaction_id=self.transaction_id,
            buyer_id="buyer-sec",
            merchant_id="merchant-sec",
            mandate_id="mandate-sec",
            mandate_version=1,
            policy_version=1,
            cart_hash="b" * 64,
            amount_paise=10000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
        )

        self.valid_outcomes = [
            SecurityControlOutcome(
                control_name="MANDATE_EVALUATION", passed=True, decision=PolicyDecision.ALLOW
            ),
            SecurityControlOutcome(
                control_name="MERCHANT_POLICY", passed=True, decision=PolicyDecision.ALLOW
            ),
            SecurityControlOutcome(
                control_name="CART_INTEGRITY", passed=True, decision=PolicyDecision.ALLOW
            ),
            SecurityControlOutcome(
                control_name="BUDGET_RESERVATION", passed=True, decision=PolicyDecision.ALLOW
            ),
            SecurityControlOutcome(
                control_name="REPLAY_PROTECTION", passed=True, decision=PolicyDecision.ALLOW
            ),
            SecurityControlOutcome(
                control_name="NONCE_VALIDATION", passed=True, decision=PolicyDecision.ALLOW
            ),
        ]
        self.auth_allow = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=self.valid_outcomes,
        )

    # ------------------------------------------------------------------
    # 1. Zero Credential Leakage
    # ------------------------------------------------------------------

    def test_http_adapter_credentials_never_leak_in_str_or_repr(self) -> None:
        secret_key = SecretString("rzp_live_SUPER_SECRET_KEY_12345")
        secret_pass = SecretString("SUPER_SECRET_PASSWORD_67890")
        adapter = RazorpayHttpAdapter(key_id=secret_key, key_secret=secret_pass)

        # Confirm representation is safe
        s_repr = repr(adapter)
        s_str = str(adapter)
        self.assertNotIn("rzp_live_SUPER_SECRET_KEY_12345", s_repr)
        self.assertNotIn("SUPER_SECRET_PASSWORD_67890", s_repr)
        self.assertNotIn("rzp_live_SUPER_SECRET_KEY_12345", s_str)
        self.assertNotIn("SUPER_SECRET_PASSWORD_67890", s_str)

    # ------------------------------------------------------------------
    # 2. Prompt & Authority Injection Inertness
    # ------------------------------------------------------------------

    def test_authority_override_fields_stripped_by_tool_proxy(self) -> None:
        malicious_input = {
            "transaction_id": self.transaction_id,
            "merchant_id": "merchant-sec",
            "buyer_id": "buyer-sec",
            "mandate_id": "mandate-sec",
            "amount_paise": 10000,
            "currency": "INR",
            "cart_hash": "b" * 64,
            "admin_override": True,
            "bypass_auth": True,
            "skip_policy": True,
            "payment_approved": True,
        }

        sanitized = self.proxy.sanitize_untrusted_input(malicious_input)
        self.assertNotIn("admin_override", sanitized)
        self.assertNotIn("bypass_auth", sanitized)
        self.assertNotIn("skip_policy", sanitized)
        self.assertNotIn("payment_approved", sanitized)
        self.assertEqual(sanitized["amount_paise"], 10000)

    # ------------------------------------------------------------------
    # 3. SSRF & URL Injection Safety
    # ------------------------------------------------------------------

    def test_tool_proxy_rejects_ssrf_urls(self) -> None:
        unsafe_urls = [
            "http://localhost:8080/admin",
            "http://127.0.0.1/evil",
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
            "data:text/html,<script>alert(1)</script>",
        ]
        for url in unsafe_urls:
            self.assertFalse(self.proxy.validate_url_safety(url))

            raw_input = {
                "transaction_id": self.transaction_id,
                "amount_paise": 10000,
                "target_url": url,
            }
            resp = self.proxy.invoke_execution_tool(
                raw_tool_input=raw_input,
                authorization_result=self.auth_allow,
                transaction=self.transaction,
            )
            self.assertFalse(resp.success)
            self.assertIn("unsafe target URL", resp.safe_message)


if __name__ == "__main__":
    unittest.main()
