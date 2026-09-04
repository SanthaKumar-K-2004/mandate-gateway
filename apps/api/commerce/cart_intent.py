"""
Mandate Gateway — Multi-Item Intent Model & Extraction (M28)
Workstream 1 & 2 — Domain models and intent parsing for multi-item shopping requests.
Factual product data is strictly prohibited from LLM hallucination.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CartOptimizationStrategy(str, Enum):
    """Supported cart optimization strategies."""

    LOWEST_TOTAL_PRICE = "LOWEST_TOTAL_PRICE"
    BEST_VALUE = "BEST_VALUE"
    FEWEST_MERCHANTS = "FEWEST_MERCHANTS"
    HIGHEST_TRUST = "HIGHEST_TRUST"
    BALANCED = "BALANCED"


@dataclass
class ShoppingItemIntent:
    """Intent specifications for an individual item in a multi-item request."""

    item_name: str
    normalized_query: str
    quantity: int = 1
    max_item_budget_paise: Optional[int] = None
    required_attributes: List[str] = field(default_factory=list)
    optional_preferences: List[str] = field(default_factory=list)
    substitution_allowed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_name": self.item_name,
            "normalized_query": self.normalized_query,
            "quantity": self.quantity,
            "max_item_budget_paise": self.max_item_budget_paise,
            "required_attributes": self.required_attributes,
            "optional_preferences": self.optional_preferences,
            "substitution_allowed": self.substitution_allowed,
        }


@dataclass
class ShoppingRequest:
    """Multi-item shopping request specification."""

    request_id: str
    prompt: str
    items: List[ShoppingItemIntent]
    total_budget_paise: int
    max_merchant_count: int = 3
    preferred_merchants: List[str] = field(default_factory=list)
    excluded_merchants: List[str] = field(default_factory=list)
    verified_only: bool = True
    optimization_strategy: CartOptimizationStrategy = CartOptimizationStrategy.BEST_VALUE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "prompt": self.prompt,
            "items": [item.to_dict() for item in self.items],
            "total_budget_paise": self.total_budget_paise,
            "max_merchant_count": self.max_merchant_count,
            "preferred_merchants": self.preferred_merchants,
            "excluded_merchants": self.excluded_merchants,
            "verified_only": self.verified_only,
            "optimization_strategy": self.optimization_strategy.value,
        }


class MultiItemIntentExtractor:
    """
    Parses multi-item intent specifications from natural language prompts.
    Extracts item queries, quantities, total budget limits, and strategy.
    """

    @classmethod
    def parse_prompt(self, prompt: str, default_budget_paise: int = 50000) -> ShoppingRequest:
        """Parse natural language prompt into ShoppingRequest model."""
        req_id = f"shop_req_{uuid.uuid4().hex[:10]}"
        clean_prompt = prompt.strip()

        # Extract budget limit (e.g., "under ₹500", "under 1000", "milk ₹300", "coffee 150", "tea for 200")
        budget_paise = default_budget_paise

        m1 = re.search(
            r"(?:under|below|within|for|@)\s*(?:₹|Rs\.?|INR)?\s*(\d+(?:,\d+)*)",
            clean_prompt,
            re.IGNORECASE,
        )
        m2 = re.search(r"(?:₹|Rs\.?|INR)\s*(\d+(?:,\d+)*)", clean_prompt, re.IGNORECASE)
        m3 = re.search(r"\b(\d+(?:,\d+)*)\s*(?:INR|rupees)?$", clean_prompt, re.IGNORECASE)

        match = m1 or m2 or m3
        if match:
            raw_val = match.group(1).replace(",", "")
            val = int(raw_val)
            if val > 0:
                budget_paise = val * 100

        # Extract items by stripping budget text cleanly
        items_part = clean_prompt
        if match:
            items_part = clean_prompt[: match.start()] + " " + clean_prompt[match.end() :]

        items_part = re.sub(
            r"^(?:find|buy|get|build|search for)\s+", "", items_part.strip(), flags=re.IGNORECASE
        )
        items_part = re.sub(
            r"\b(?:under|below|within|for|@|₹|Rs\.?|INR|rupees)\b",
            "",
            items_part,
            flags=re.IGNORECASE,
        ).strip()

        # Split on commas or " and "
        raw_items = re.split(r",|\s+and\s+", items_part, flags=re.IGNORECASE)
        intents: List[ShoppingItemIntent] = []

        for raw_item in raw_items:
            item_clean = raw_item.strip()
            if not item_clean or item_clean.isdigit():
                continue

            # Check quantity prefix (e.g. "2 notebooks", "3 pens")
            qty = 1
            qty_match = re.match(r"^(\d+)\s+(.+)$", item_clean)
            if qty_match:
                qty = int(qty_match.group(1))
                item_clean = qty_match.group(2).strip()

            intents.append(
                ShoppingItemIntent(
                    item_name=item_clean.capitalize(),
                    normalized_query=item_clean.lower(),
                    quantity=qty,
                )
            )

        if not intents:
            fallback_query = "coffee"
            intents.append(
                ShoppingItemIntent(
                    item_name=fallback_query.capitalize(),
                    normalized_query=fallback_query,
                    quantity=1,
                )
            )

        # Detect strategy preferences
        strategy = CartOptimizationStrategy.BEST_VALUE
        if "cheapest" in clean_prompt.lower() or "lowest" in clean_prompt.lower():
            strategy = CartOptimizationStrategy.LOWEST_TOTAL_PRICE
        elif "fewest merchant" in clean_prompt.lower() or "single merchant" in clean_prompt.lower():
            strategy = CartOptimizationStrategy.FEWEST_MERCHANTS

        return ShoppingRequest(
            request_id=req_id,
            prompt=prompt,
            items=intents,
            total_budget_paise=budget_paise,
            optimization_strategy=strategy,
        )
