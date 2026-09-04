"""
LLM Decision Models & Structured Output Schemas.
Enforces strict Pydantic schemas for LLM reasoning output.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ShoppingItemIntent(BaseModel):
    """Structured intent representation for a single requested item."""

    item_name: str
    target_category: Optional[str] = None
    quantity: int = Field(default=1, ge=1)
    max_unit_price_paise: Optional[int] = None
    preferred_brands: List[str] = Field(default_factory=list)


class AICommerceDecision(BaseModel):
    """
    Structured Output Schema for LLM Decision Reasoning.
    NOTE: This model represents AI reasoning and suggestions.
    It carries ZERO direct authorization to move money or execute payments.
    """

    intent_summary: str
    items: List[ShoppingItemIntent] = Field(default_factory=list)
    total_budget_paise: int = Field(ge=0)
    currency: str = "INR"
    user_preferences: List[str] = Field(default_factory=list)
    research_strategy: str = "DEFAULT_MULTI_SOURCE"
    recommended_candidates: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning: str
    risk_signals: List[str] = Field(default_factory=list)
    prompt_injection_detected: bool = False
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)
    requires_human_confirmation: bool = True
    allowed_action: str = "RESEARCH_ONLY"

    def is_safe_for_planning(self) -> bool:
        """Determines if the decision output is safe to proceed to purchase planning."""
        if self.prompt_injection_detected:
            return False
        if self.allowed_action not in ("RESEARCH_ONLY", "PREPARE_PURCHASE_PLAN"):
            return False
        return True
