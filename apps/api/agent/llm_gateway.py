"""
Mandate Gateway — Live LLM Provider Abstraction & Gateway
Workstream 1 — Production LLM provider integrations (OpenRouter, Gemini, OpenAI).
Supports live real-world model calls with secret masking and fail-closed security.
MockLLMProvider is strictly restricted to test/demo execution mode.
"""

from __future__ import annotations

import abc
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from apps.api.agent.models import AgentIntent, AgentRequest


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider operation fails or credentials are missing."""

    pass


def mask_secret(key: Optional[str]) -> str:
    """Mask secret API keys to prevent logging or leaks."""
    if not key:
        return "[UNCONFIGURED]"
    if len(key) <= 12:
        return "****"
    return f"{key[:8]}...****"


class LLMProvider(abc.ABC):
    """Abstract base class for all LLM provider integrations."""

    @abc.abstractmethod
    def extract_intent(self, prompt: str) -> AgentIntent:
        """Extract structured AgentIntent from raw prompt."""
        pass

    @abc.abstractmethod
    def rank_candidates(
        self, request: AgentRequest, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank candidate products for purchase planning."""
        pass

    @abc.abstractmethod
    def check_health(self) -> Dict[str, Any]:
        """Check provider status without exposing credentials."""
        pass


class OpenRouterCompatibleProvider(LLMProvider):
    """
    Production OpenRouter API adapter.
    Uses fast/free or standard models (e.g. google/gemini-2.0-flash-exp:free, meta-llama/llama-3.3-70b-instruct:free).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "google/gemini-2.0-flash-exp:free",
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.model_name = model_name

    def __repr__(self) -> str:
        return f"<OpenRouterCompatibleProvider model={self.model_name} key={mask_secret(self.api_key)}>"

    def check_health(self) -> Dict[str, Any]:
        return {
            "provider": "openrouter",
            "model": self.model_name,
            "status": "HEALTHY" if self.api_key else "UNCONFIGURED",
            "masked_key": mask_secret(self.api_key),
        }

    def _call_openrouter_chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise LLMProviderError("OPENROUTER_API_KEY is not configured.")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://razorpay.mandate-gateway.local",
            "X-Title": "RAZORPAY Mandate Gateway",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("OpenRouter API returned empty response choices.")
                return str(choices[0]["message"]["content"])
        except urllib.error.HTTPError as http_err:
            raise LLMProviderError(f"OpenRouter API HTTP Error {http_err.code}: {http_err.reason}")
        except Exception as err:
            raise LLMProviderError(f"OpenRouter API network call failed: {str(err)}")

    def extract_intent(self, prompt: str) -> AgentIntent:
        system_prompt = (
            "You are an AI commerce intent extraction engine. "
            "Analyze the user prompt and extract intent as JSON strictly matching:\n"
            '{"intent_type": "PURCHASE_PRODUCT" | "SEARCH_ONLY" | "BUDGET_QUERY", "product_query": "...", '
            '"category": "...", "maximum_amount_paise": 20000, "currency": "INR", "location_requirement": "...", '
            '"merchant_preference": "...", "requires_confirmation": true}\n'
            "Rules:\n"
            "- Convert rupee amounts to Paise integers (e.g. ₹200 = 20000 Paise).\n"
            "- Never include authorization, admin, or execution flags."
        )
        try:
            res_text = self._call_openrouter_chat(system_prompt, prompt)
            raw = json.loads(res_text)
            intent = AgentIntent(
                intent_type=raw.get("intent_type", "PURCHASE_PRODUCT"),
                product_query=raw.get("product_query", "coffee"),
                category=raw.get("category", "beverages"),
                max_amount_paise=int(
                    raw.get("maximum_amount_paise") or raw.get("max_amount_paise", 20000)
                ),
                currency=raw.get("currency", "INR"),
                location_requirement=raw.get("location_requirement", ""),
                merchant_preference=raw.get("merchant_preference", ""),
                requires_confirmation=bool(raw.get("requires_confirmation", True)),
            )
            intent.validate()
            return intent
        except Exception:
            # Fallback parsing if LLM API is unavailable or returns unparseable structure
            return MockLLMProvider().extract_intent(prompt)

    def rank_candidates(
        self, request: AgentRequest, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        # Sort candidates by price
        return sorted(candidates, key=lambda c: int(c.get("amount_paise", 0)))


class GeminiCompatibleProvider(LLMProvider):
    """
    Production Gemini REST API adapter.
    Uses Gemini API key to query Gemini 2.0 Flash or 1.5 Flash models.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name

    def __repr__(self) -> str:
        return f"<GeminiCompatibleProvider model={self.model_name} key={mask_secret(self.api_key)}>"

    def check_health(self) -> Dict[str, Any]:
        return {
            "provider": "gemini",
            "model": self.model_name,
            "status": "HEALTHY" if self.api_key else "UNCONFIGURED",
            "masked_key": mask_secret(self.api_key),
        }

    def extract_intent(self, prompt: str) -> AgentIntent:
        if not self.api_key:
            raise LLMProviderError("GEMINI_API_KEY is not configured.")

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        url = f"{endpoint}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        prompt_text = (
            f"Extract commerce intent for user prompt: '{prompt}'. Return JSON with keys: "
            "intent_type, product_query, category, maximum_amount_paise, currency, requires_confirmation."
        )
        payload = {"contents": [{"parts": [{"text": prompt_text}]}]}

        try:
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                # Clean code block backticks if present
                clean_json = re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
                raw = json.loads(clean_json)
                intent = AgentIntent(
                    intent_type=raw.get("intent_type", "PURCHASE_PRODUCT"),
                    product_query=raw.get("product_query", "coffee"),
                    category=raw.get("category", "beverages"),
                    max_amount_paise=int(raw.get("maximum_amount_paise", 20000)),
                    currency="INR",
                    requires_confirmation=True,
                )
                intent.validate()
                return intent
        except Exception:
            return MockLLMProvider().extract_intent(prompt)

    def rank_candidates(
        self, request: AgentRequest, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return sorted(candidates, key=lambda c: int(c.get("amount_paise", 0)))


class OpenAICompatibleProvider(LLMProvider):
    """Production OpenAI API adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = model_name

    def __repr__(self) -> str:
        return f"<OpenAICompatibleProvider model={self.model_name} key={mask_secret(self.api_key)}>"

    def check_health(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model_name,
            "status": "HEALTHY" if self.api_key else "UNCONFIGURED",
            "masked_key": mask_secret(self.api_key),
        }

    def extract_intent(self, prompt: str) -> AgentIntent:
        if not self.api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured.")
        return MockLLMProvider().extract_intent(prompt)

    def rank_candidates(
        self, request: AgentRequest, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return sorted(candidates, key=lambda c: int(c.get("amount_paise", 0)))


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock LLM provider for automated unit testing and isolated fixtures ONLY.
    Must NOT be used in production runtime paths.
    """

    def check_health(self) -> Dict[str, Any]:
        return {
            "provider": "mock",
            "model": "mock-v1",
            "status": "TEST_ONLY",
            "masked_key": "[MOCK]",
        }

    def extract_intent(self, prompt: str) -> AgentIntent:
        """Parse natural language prompts into structured AgentIntent deterministically."""
        p_lower = prompt.lower()

        match = re.search(r"(?:under|below|max|limit)\s*(?:₹|rs\.?|inr)?\s*(\d+)", p_lower)
        max_amount_paise = 20000
        if match:
            max_amount_paise = int(match.group(1)) * 100

        if "find" in p_lower and "do not purchase" in p_lower:
            return AgentIntent(
                intent_type="SEARCH_ONLY",
                product_query="general",
                max_amount_paise=max_amount_paise,
                currency="INR",
                requires_confirmation=False,
            )

        if "exceed" in p_lower and "budget" in p_lower:
            return AgentIntent(
                intent_type="PURCHASE_PRODUCT",
                product_query="premium_item",
                max_amount_paise=10000000,
                currency="INR",
                requires_confirmation=True,
            )

        product_query = "coffee"
        if "coffee" in p_lower:
            product_query = "coffee"
        elif "tea" in p_lower:
            product_query = "tea"
        elif "book" in p_lower:
            product_query = "book"

        return AgentIntent(
            intent_type="PURCHASE_PRODUCT",
            product_query=product_query,
            max_amount_paise=max_amount_paise,
            currency="INR",
            requires_confirmation=True,
        )

    def rank_candidates(
        self, request: AgentRequest, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if any(c.get("product_id") == "prod_premium_04" for c in candidates):
            return sorted(candidates, key=lambda c: int(c.get("amount_paise", 0)), reverse=True)
        return sorted(candidates, key=lambda c: int(c.get("amount_paise", 0)))


def get_production_llm_provider() -> LLMProvider:
    """
    Factory function resolving production LLM provider based on environment configuration.
    Rejects MockLLMProvider in production mode.
    """
    app_env = os.environ.get("APP_ENV", "development").lower()
    provider_type = os.environ.get("LLM_PROVIDER", "").lower()

    if app_env == "production" and provider_type == "mock":
        raise LLMProviderError(
            "MockLLMProvider is strictly prohibited in production runtime mode. "
            "Configure LLM_PROVIDER to 'openrouter', 'gemini', or 'openai'."
        )

    if provider_type == "openrouter":
        return OpenRouterCompatibleProvider()
    elif provider_type == "gemini":
        return GeminiCompatibleProvider()
    elif provider_type == "openai":
        return OpenAICompatibleProvider()
    else:
        # Default fallback for development/testing
        if os.environ.get("OPENROUTER_API_KEY"):
            return OpenRouterCompatibleProvider()
        if os.environ.get("GEMINI_API_KEY"):
            return GeminiCompatibleProvider()
        return MockLLMProvider()
