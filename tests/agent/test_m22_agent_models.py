"""
M22 AI Agent Models Unit Test Suite
===================================
Workstream 1 — Verifies typed AI agent domain models, intent validation,
and fail-closed rejection of invalid LLM intent structures.
"""

from __future__ import annotations

import unittest
from apps.api.agent.models import AgentIntent


class TestM22AgentModels(unittest.TestCase):
    """AI agent domain model test suite."""

    def test_01_valid_agent_intent(self) -> None:
        """Verify valid agent intent passes validation."""
        intent = AgentIntent(
            intent_type="PURCHASE_PRODUCT",
            product_query="coffee",
            max_amount_paise=20000,
            currency="INR",
        )
        # Should validate without error
        intent.validate()

    def test_02_invalid_intent_type_rejected(self) -> None:
        """Verify untrusted intent_type raises ValueError."""
        intent = AgentIntent(
            intent_type="UNTRUSTED_EXECUTE_PAYMENT",
            product_query="coffee",
            max_amount_paise=20000,
        )
        with self.assertRaises(ValueError):
            intent.validate()

    def test_03_negative_amount_rejected(self) -> None:
        """Verify negative or zero max_amount_paise raises ValueError."""
        intent = AgentIntent(
            intent_type="PURCHASE_PRODUCT",
            product_query="coffee",
            max_amount_paise=-500,
        )
        with self.assertRaises(ValueError):
            intent.validate()

    def test_04_unsupported_currency_rejected(self) -> None:
        """Verify non-INR currency raises ValueError."""
        intent = AgentIntent(
            intent_type="PURCHASE_PRODUCT",
            product_query="coffee",
            max_amount_paise=20000,
            currency="USD",
        )
        with self.assertRaises(ValueError):
            intent.validate()


if __name__ == "__main__":
    unittest.main()
