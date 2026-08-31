"""
Mandate Gateway — Total Cost Truth Engine (M28)
Workstream 6 — Evaluates exact known product subtotals vs unknown cost components.
CRITICAL RULE: If shipping, tax, or fees are unverified, DO NOT estimate. Mark as UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apps.api.commerce.canonical_product import CanonicalProduct


@dataclass
class CartCostSummary:
    """Total cost breakdown with explicit known vs unknown components."""

    product_subtotal_paise: int
    shipping_cost_paise: Optional[int]
    tax_paise: Optional[int]
    platform_fee_paise: Optional[int]
    total_known_cost_paise: int
    unknown_cost_components: List[str] = field(default_factory=list)

    @property
    def is_total_fully_verified(self) -> bool:
        """Check if total cost is fully verified with zero unknown components."""
        return len(self.unknown_cost_components) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_subtotal_paise": self.product_subtotal_paise,
            "product_subtotal_inr": round(self.product_subtotal_paise / 100.0, 2),
            "shipping_cost_paise": self.shipping_cost_paise,
            "shipping_cost_inr": (
                round(self.shipping_cost_paise / 100.0, 2)
                if self.shipping_cost_paise is not None
                else None
            ),
            "tax_paise": self.tax_paise,
            "tax_inr": round(self.tax_paise / 100.0, 2) if self.tax_paise is not None else None,
            "platform_fee_paise": self.platform_fee_paise,
            "platform_fee_inr": (
                round(self.platform_fee_paise / 100.0, 2)
                if self.platform_fee_paise is not None
                else None
            ),
            "total_known_cost_paise": self.total_known_cost_paise,
            "total_known_cost_inr": round(self.total_known_cost_paise / 100.0, 2),
            "unknown_cost_components": self.unknown_cost_components,
            "is_total_fully_verified": len(self.unknown_cost_components) == 0,
        }


class CartCostEngine:
    """
    Total Cost Truth Engine.
    Computes verified product costs and flags unverified shipping/tax fields as UNKNOWN.
    """

    @classmethod
    def calculate_cart_cost(
        cls,
        selected_products: List[CanonicalProduct],
        quantities: Optional[List[int]] = None,
        verified_shipping_paise: Optional[int] = None,
        verified_tax_paise: Optional[int] = None,
    ) -> CartCostSummary:
        """Calculate total known costs and flag unverified components as UNKNOWN."""
        if not quantities:
            quantities = [1] * len(selected_products)

        subtotal = 0
        for prod, qty in zip(selected_products, quantities):
            subtotal += prod.price_paise * qty

        unknowns: List[str] = []
        known_total = subtotal

        # Shipping cost verification
        if verified_shipping_paise is not None:
            known_total += verified_shipping_paise
        else:
            unknowns.append("SHIPPING_COST")

        # Tax verification
        if verified_tax_paise is not None:
            known_total += verified_tax_paise
        else:
            unknowns.append("MERCHANT_TAX")

        return CartCostSummary(
            product_subtotal_paise=subtotal,
            shipping_cost_paise=verified_shipping_paise,
            tax_paise=verified_tax_paise,
            platform_fee_paise=0,
            total_known_cost_paise=known_total,
            unknown_cost_components=unknowns,
        )
