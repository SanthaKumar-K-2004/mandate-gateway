"""
M22 LLM Gateway Unit Test Suite
================================
Workstream 2 — Verifies LLM provider abstraction, MockLLMProvider intent extraction,
and fail-safe behavior when vendor API keys are unconfigured.
"""

from __future__ import annotations

import unittest
from apps.api.agent.llm_gateway import (
    GeminiCompatibleProvider,
    LLMProviderError,
    MockLLMProvider,
    OpenAICompatibleProvider,
)


class TestM22LLMGateway(unittest.TestCase):
    """LLM gateway test suite."""

    def test_01_mock_provider_intent_extraction(self) -> None:
        """Verify MockLLMProvider extracts structured intent cleanly."""
        provider = MockLLMProvider()
        intent = provider.extract_intent("Buy me a coffee under ₹200")
        self.assertEqual(intent.intent_type, "PURCHASE_PRODUCT")
        self.assertEqual(intent.product_query, "coffee")
        self.assertEqual(intent.max_amount_paise, 20000)

    def test_02_openai_provider_fails_without_key(self) -> None:
        """Verify OpenAI provider raises LLMProviderError when key is missing."""
        provider = OpenAICompatibleProvider(api_key=None)
        with self.assertRaises(LLMProviderError):
            provider.extract_intent("Buy coffee")

    def test_03_gemini_provider_fails_without_key(self) -> None:
        """Verify Gemini provider raises LLMProviderError when key is missing."""
        provider = GeminiCompatibleProvider(api_key=None)
        with self.assertRaises(LLMProviderError):
            provider.extract_intent("Buy coffee")


if __name__ == "__main__":
    unittest.main()
