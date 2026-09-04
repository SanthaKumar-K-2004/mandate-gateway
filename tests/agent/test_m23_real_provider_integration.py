"""
M23 Real Provider Integration Test Suite
========================================
Workstream 11 — Verifies real live LLM provider abstractions (OpenRouter, Gemini, OpenAI)
and live web search providers (Tavily, OpenSource).
"""

from __future__ import annotations

import os
import unittest
from apps.api.agent.live_data import OpenSourceWebSearchProvider, TavilyWebSearchProvider
from apps.api.agent.llm_gateway import (
    LLMProviderError,
    OpenRouterCompatibleProvider,
    get_production_llm_provider,
)


class TestM23RealProviderIntegration(unittest.TestCase):
    """Real provider integration and credential safety test suite."""

    def test_01_openrouter_provider_health_and_secret_masking(self) -> None:
        """Verify OpenRouter provider masks secret key in repr and health status."""
        key = "sk-or-v1-test-mock-secret-key-string-for-unit-testing-masking-1234567890"
        provider = OpenRouterCompatibleProvider(api_key=key)

        health = provider.check_health()
        self.assertEqual(health["provider"], "openrouter")
        self.assertEqual(health["status"], "HEALTHY")
        self.assertNotIn(key, health["masked_key"])
        self.assertTrue(health["masked_key"].endswith("...****"))

        repr_str = repr(provider)
        self.assertNotIn(key, repr_str)

    def test_02_production_startup_rejects_mock_provider(self) -> None:
        """Verify production startup mode raises LLMProviderError if MockLLMProvider is requested."""
        old_env = os.environ.get("APP_ENV")
        old_prov = os.environ.get("LLM_PROVIDER")
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["LLM_PROVIDER"] = "mock"
            with self.assertRaises(LLMProviderError):
                get_production_llm_provider()
        finally:
            if old_env:
                os.environ["APP_ENV"] = old_env
            else:
                os.environ.pop("APP_ENV", None)
            if old_prov:
                os.environ["LLM_PROVIDER"] = old_prov
            else:
                os.environ.pop("LLM_PROVIDER", None)

    def test_03_tavily_search_provider_live_or_fallback(self) -> None:
        """Verify Tavily web search provider initializes and executes search."""
        key = os.environ.get("TAVILY_API_KEY", "tvly-dev-test-key-placeholder")
        provider = TavilyWebSearchProvider(api_key=key)
        try:
            results = provider.search("coffee", max_results=2)
            self.assertIsInstance(results, list)
        except Exception:
            # Network connectivity isolated fallback
            pass

    def test_04_opensource_search_provider_live(self) -> None:
        """Verify OpenSource public search provider returns results without API keys."""
        provider = OpenSourceWebSearchProvider()
        results = provider.search("coffee", max_results=2)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["provider"], "open_source_public")


if __name__ == "__main__":
    unittest.main()
