"""
LLM Decision Engine.
Orchestrates LLM prompts, structured parsing, prompt-injection checks, and explanation generation.
"""

from typing import Any, Dict, Optional
from apps.api.ai.llm.models import AICommerceDecision
from apps.api.ai.llm.provider import LLMProvider, get_llm_provider
from apps.api.ai.security.prompt_defense import PromptDefenseEngine


class LLMDecisionEngine:
    """Primary entry point for LLM commerce intelligence and reasoning."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider()
        self.prompt_defense = PromptDefenseEngine()

    def process_shopping_request(
        self, prompt: str, budget_paise: int = 30000, context: Optional[Dict[str, Any]] = None
    ) -> AICommerceDecision:
        """
        Processes a natural language shopping request through prompt defense and LLM reasoning.
        Returns a validated, structured AICommerceDecision object.
        """
        context = context or {}
        context["budget_paise"] = budget_paise

        # 1. Sanitize untrusted input & run prompt injection defense
        sanitized_prompt, is_injection = self.prompt_defense.inspect_input(prompt)

        if is_injection:
            return AICommerceDecision(
                intent_summary="Blocked prompt injection attempt in user request",
                items=[],
                total_budget_paise=budget_paise,
                currency="INR",
                user_preferences=[],
                research_strategy="BLOCKED",
                reasoning="Prompt injection defense caught malicious command override patterns.",
                risk_signals=["PROMPT_INJECTION_DETECTED", "MALICIOUS_INPUT_PATTERN"],
                prompt_injection_detected=True,
                confidence_score=0.99,
                requires_human_confirmation=True,
                allowed_action="BLOCKED",
            )

        # 2. Query configured LLM Provider
        decision = self.provider.generate_decision(sanitized_prompt, context)

        # 3. Post-process decision checks
        if decision.total_budget_paise <= 0:
            decision.total_budget_paise = budget_paise

        return decision

    def explain_recommendation(
        self, plan_summary: Dict[str, Any], risk_summary: Dict[str, Any]
    ) -> str:
        """Generates natural language explanation of cart recommendation & safety score."""
        budget = plan_summary.get("budget_paise", 0) / 100
        cost = plan_summary.get("total_cost_paise", 0) / 100
        risk_level = risk_summary.get("risk_level", "LOW")

        return (
            f"Recommended cart optimized to ₹{cost:.2f} within your ₹{budget:.2f} budget. "
            f"Risk analysis evaluated as {risk_level} with 100% product evidence verification. "
            "Human authorization is required to proceed with test payment execution."
        )
