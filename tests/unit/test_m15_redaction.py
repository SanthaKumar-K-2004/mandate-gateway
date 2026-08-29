"""
Unit tests for M15 Sensitive Data Redaction Engine.
"""

import unittest

from apps.api.app.logging import redact_value
from apps.api.config.types import SecretString


class TestM15RedactionUnit(unittest.TestCase):
    def test_recursive_dict_redaction(self) -> None:
        payload = {
            "merchant_id": "mer_123",
            "api_key": "rzp_live_secret_key_999",
            "nested": {
                "bearer_token": "Bearer abc.def.ghi",
                "secret_string": SecretString("super_secret_payload"),
                "safe_field": "public_data",
            },
            "array": [
                {"authorization": "Bearer token123"},
                {"cvv": "123"},
                {"safe": "ok"},
            ],
        }

        redacted = redact_value(payload)

        self.assertEqual(redacted["merchant_id"], "mer_123")
        self.assertEqual(redacted["api_key"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["bearer_token"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["secret_string"], "[REDACTED]")
        self.assertEqual(redacted["nested"]["safe_field"], "public_data")
        self.assertEqual(redacted["array"][0]["authorization"], "[REDACTED]")
        self.assertEqual(redacted["array"][1]["cvv"], "[REDACTED]")
        self.assertEqual(redacted["array"][2]["safe"], "ok")

        # Original object must not be mutated
        self.assertNotEqual(payload["api_key"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
