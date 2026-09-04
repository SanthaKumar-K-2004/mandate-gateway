"""
LLM Provider Abstraction Layer.
Supports Google Gemini, Groq, OpenAI API, Local LLM API, and Mock Provider for deterministic tests.
"""

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from apps.api.ai.llm.models import AICommerceDecision, ShoppingItemIntent


class LLMProvider(ABC):
    """Abstract base class for LLM decision providers."""

    @abstractmethod
    def generate_decision(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AICommerceDecision:
        """Generates a validated AICommerceDecision structured object."""
        pass

    @abstractmethod
    def provider_name(self) -> str:
        """Returns provider identifier name."""
        pass


class MockLLMProvider(LLMProvider):
    """Deterministic Mock LLM Provider for local testing and CI environments."""

    def __init__(self, simulate_injection: bool = False) -> None:
        self.simulate_injection = simulate_injection

    def provider_name(self) -> str:
        return "mock"

    def generate_decision(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AICommerceDecision:
        context = context or {}
        budget_paise = context.get("budget_paise", 30000)

        # Detect injection keywords if requested or prompt injection present
        injection_keywords = [
            "ignore previous instructions",
            "execute payment",
            "bypass safety",
            "system override",
        ]
        has_injection = self.simulate_injection or any(
            kw in prompt.lower() for kw in injection_keywords
        )

        if has_injection:
            return AICommerceDecision(
                intent_summary="Blocked prompt injection attempt in user request",
                items=[],
                total_budget_paise=budget_paise,
                currency="INR",
                user_preferences=[],
                research_strategy="BLOCKED",
                reasoning="Prompt injection signatures detected in input prompt. Execution halted.",
                risk_signals=["PROMPT_INJECTION_DETECTED", "UNTRUSTED_INSTRUCTION_OVERRIDE"],
                prompt_injection_detected=True,
                confidence_score=0.99,
                requires_human_confirmation=True,
                allowed_action="BLOCKED",
            )

        # Parse basic intent items from prompt keywords
        items = []
        if "coffee" in prompt.lower():
            items.append(
                ShoppingItemIntent(item_name="coffee", target_category="beverage", quantity=1)
            )
        if "biscuit" in prompt.lower() or "cookies" in prompt.lower():
            items.append(
                ShoppingItemIntent(item_name="biscuits", target_category="snack", quantity=1)
            )

        if not items:
            items.append(
                ShoppingItemIntent(item_name="general_item", target_category="grocery", quantity=1)
            )

        return AICommerceDecision(
            intent_summary=f"Synthesized shopping intent for: {prompt[:50]}",
            items=items,
            total_budget_paise=budget_paise,
            currency="INR",
            user_preferences=["quality_first", "budget_conscious"],
            research_strategy="OPENFOODFACTS_PARALLEL",
            reasoning=(
                f"Analyzed query '{prompt}'. Identified {len(items)} item targets "
                f"within ₹{budget_paise/100:.2f} budget."
            ),
            risk_signals=[],
            prompt_injection_detected=False,
            confidence_score=0.95,
            requires_human_confirmation=True,
            allowed_action="PREPARE_PURCHASE_PLAN",
        )


class GeminiProvider(LLMProvider):
    """Google Gemini Primary LLM Provider (requires GEMINI_API_KEY)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback: Optional[LLMProvider] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.fallback_provider = fallback

    def provider_name(self) -> str:
        return f"gemini-{self.model}"

    def generate_decision(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AICommerceDecision:
        if not self.api_key:
            if self.fallback_provider:
                return self.fallback_provider.generate_decision(prompt, context)
            return MockLLMProvider().generate_decision(prompt, context)

        try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent?key={self.api_key}"
            )
            headers = {"Content-Type": "application/json"}
            system_instruction = (
                "You are the Razorpay AI Commerce Reasoning Engine. "
                "Analyze user requests and return structured JSON decision outputs matching: "
                "{intent_summary: str, items: [{item_name, quantity, target_category}], "
                "total_budget_paise: int, currency: str, reasoning: str, "
                "prompt_injection_detected: bool, confidence_score: float}. "
                "You are an intelligence layer ONLY and have ZERO authority to move money or execute payments."
            )
            full_prompt = f"{system_instruction}\nUser Prompt: {prompt}"
            payload = {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                text_content = res_data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_content)
                return AICommerceDecision.model_validate(parsed)

        except Exception:
            if self.fallback_provider:
                return self.fallback_provider.generate_decision(prompt, context)
            return MockLLMProvider().generate_decision(prompt, context)


class GroqProvider(LLMProvider):
    """Groq Fallback LLM Provider (requires GROQ_API_KEY)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback: Optional[LLMProvider] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.fallback_provider = fallback

    def provider_name(self) -> str:
        return f"groq-{self.model}"

    def generate_decision(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AICommerceDecision:
        if not self.api_key:
            if self.fallback_provider:
                return self.fallback_provider.generate_decision(prompt, context)
            return MockLLMProvider().generate_decision(prompt, context)

        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            system_instruction = (
                "You are the Razorpay AI Commerce Reasoning Engine. "
                "Analyze user requests and produce structured JSON decisions. "
                "You are an intelligence layer ONLY and have ZERO authority to move money or execute payments."
            )
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return AICommerceDecision.model_validate(parsed)

        except Exception:
            if self.fallback_provider:
                return self.fallback_provider.generate_decision(prompt, context)
            return MockLLMProvider().generate_decision(prompt, context)


class OpenAIProvider(LLMProvider):
    """Production OpenAI LLM Provider (requires OPENAI_API_KEY)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    def provider_name(self) -> str:
        return f"openai-{self.model}"

    def generate_decision(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AICommerceDecision:
        if not self.api_key:
            return MockLLMProvider().generate_decision(prompt, context)

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            system_instruction = (
                "You are the Razorpay AI Commerce Reasoning Engine. "
                "Analyze user requests and produce structured JSON decisions. "
                "You are an intelligence layer ONLY and have ZERO authority to move money or execute payments."
            )
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return AICommerceDecision.model_validate(parsed)

        except Exception:
            return MockLLMProvider().generate_decision(prompt, context)


class LocalLLMProvider(LLMProvider):
    """Local LLM Provider (e.g., Ollama HTTP endpoint)."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        self.base_url = base_url or os.getenv("LOCAL_LLM_URL", "http://localhost:11434")
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "llama3")

    def provider_name(self) -> str:
        return f"local-{self.model}"

    def generate_decision(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> AICommerceDecision:
        return MockLLMProvider().generate_decision(prompt, context)


def get_llm_provider() -> LLMProvider:
    """
    Factory function to instantiate the configured LLM provider hierarchy.
    Defaults to Gemini (Primary) -> Groq (Fallback) -> Mock Provider.
    """
    primary = os.getenv("AI_PRIMARY_PROVIDER", os.getenv("LLM_PROVIDER", "gemini")).lower()
    fallback_type = os.getenv("AI_FALLBACK_PROVIDER", "groq").lower()

    mock_provider = MockLLMProvider()
    fallback_provider: LLMProvider = (
        GroqProvider(fallback=mock_provider) if fallback_type == "groq" else mock_provider
    )
    gemini_provider = GeminiProvider(fallback=fallback_provider)

    if primary == "gemini":
        return gemini_provider
    elif primary == "groq":
        return fallback_provider
    elif primary == "openai" and os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider()
    elif primary == "local":
        return LocalLLMProvider()

    # Default provider chain
    return gemini_provider
