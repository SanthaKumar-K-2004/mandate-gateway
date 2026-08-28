"""
S02.3 — AI Intent Parser & Arithmetic Verification Unit Tests.
"""

import unittest

from agent.intent.errors import IntentErrorCode, IntentValidationError
from agent.intent.parser import AgentIntentParser


class TestAgentIntentParserUnit(unittest.TestCase):
    def test_parse_valid_single_item(self) -> None:
        raw_item = {
            "product_id": "P_SHOES_01",
            "merchant_id": "M_RUNNER",
            "name": "Running Shoes",
            "category": "footwear",
            "quantity": 2,
            "unit_price_paise": 250000,
            "subtotal_paise": 500000,
        }
        item = AgentIntentParser.parse_item(raw_item, default_merchant_id="M_RUNNER")
        subtotal = item.quantity * item.unit_price_paise
        self.assertEqual(item.product_id, "P_SHOES_01")
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price_paise, 250000)
        self.assertEqual(subtotal, 500000)

    def test_parse_item_calculates_subtotal_if_omitted(self) -> None:
        raw_item = {
            "product_id": "P_SHIRT_01",
            "name": "Cotton Shirt",
            "quantity": 3,
            "price_paise": 100000,
        }
        item = AgentIntentParser.parse_item(raw_item, default_merchant_id="M_CLOTHES")
        subtotal = item.quantity * item.unit_price_paise
        self.assertEqual(subtotal, 300000)

    def test_invalid_line_item_math_rejected(self) -> None:
        """Verify mismatched line item subtotal arithmetic raises INVALID_LINE_ITEM_MATH."""
        bad_item = {
            "product_id": "P_WATCH",
            "merchant_id": "M_TECH",
            "name": "Smart Watch",
            "quantity": 2,
            "unit_price_paise": 500000,
            "subtotal_paise": 999999,  # Wrong subtotal math (should be 1000000)
        }
        with self.assertRaises(IntentValidationError) as ctx:
            AgentIntentParser.parse_item(bad_item, default_merchant_id="M_TECH")
        self.assertEqual(ctx.exception.code, IntentErrorCode.INVALID_LINE_ITEM_MATH)

    def test_invalid_overall_cart_total_math_rejected(self) -> None:
        """Verify overall cart sum mismatch raises INVALID_LINE_ITEM_MATH."""
        payload = {
            "merchant_id": "M_TECH",
            "items": [
                {
                    "product_id": "P1",
                    "name": "Item 1",
                    "quantity": 1,
                    "unit_price_paise": 100000,
                    "subtotal_paise": 100000,
                },
                {
                    "product_id": "P2",
                    "name": "Item 2",
                    "quantity": 2,
                    "unit_price_paise": 200000,
                    "subtotal_paise": 400000,
                },
            ],
            "total_paise": 800000,  # Wrong overall total (sum of subtotals is 500000)
        }
        with self.assertRaises(IntentValidationError) as ctx:
            AgentIntentParser.parse_intent_payload(payload, default_merchant_id="M_TECH")
        self.assertEqual(ctx.exception.code, IntentErrorCode.INVALID_LINE_ITEM_MATH)

    def test_missing_mandatory_fields_rejected(self) -> None:
        bad_item = {"quantity": 1, "unit_price_paise": 1000}
        with self.assertRaises(IntentValidationError) as ctx:
            AgentIntentParser.parse_item(bad_item, default_merchant_id="M1")
        self.assertEqual(ctx.exception.code, IntentErrorCode.MISSING_MANDATORY_FIELD)

    def test_quantity_out_of_range_rejected(self) -> None:
        bad_qty_item = {
            "product_id": "P1",
            "name": "Bulk Item",
            "quantity": 5000,
            "unit_price_paise": 100,
        }
        with self.assertRaises(IntentValidationError) as ctx:
            AgentIntentParser.parse_item(bad_qty_item, default_merchant_id="M1")
        self.assertEqual(ctx.exception.code, IntentErrorCode.MALFORMED_INTENT_PAYLOAD)

    def test_unauthorized_currency_rejected(self) -> None:
        bad_curr_payload = {
            "merchant_id": "M1",
            "currency": "USD",
            "items": [{"product_id": "P1", "name": "Item", "quantity": 1, "unit_price_paise": 100}],
        }
        with self.assertRaises(IntentValidationError) as ctx:
            AgentIntentParser.parse_intent_payload(bad_curr_payload, default_merchant_id="M1")
        self.assertEqual(ctx.exception.code, IntentErrorCode.UNAUTHORIZED_CURRENCY)


if __name__ == "__main__":
    unittest.main()
