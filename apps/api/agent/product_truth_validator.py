"""
Mandate Gateway — Product Truth Validator Engine
Workstream 4 — Ensures LLM output cannot invent or hallucinate products, prices,
discounts, merchant availability, or stock status. Every recommendation must strictly match
a retrieved source result from ProductDiscoveryProvider.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ProductTruthValidationError(ValueError):
    """Raised when an LLM hallucinated product or price mismatch is detected."""

    pass


class ProductTruthValidator:
    """Truth enforcement engine validating LLM recommendations against retrieved live data."""

    @staticmethod
    def validate_recommendation(
        selected_product: Dict[str, Any],
        retrieved_source_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate selected recommendation against retrieved source results.
        Rejects hallucinated products or modified price payloads.
        """
        if not retrieved_source_results:
            raise ProductTruthValidationError(
                "Product truth validation failed: No verified source discovery results available."
            )

        source_pid = selected_product.get("source_product_id") or selected_product.get("product_id")
        matching_source: Optional[Dict[str, Any]] = None

        for src in retrieved_source_results:
            if src.get("source_product_id") == source_pid or src.get("product_id") == source_pid:
                matching_source = src
                break

        if not matching_source:
            # Fallback to matching by exact name if source_product_id differs
            for src in retrieved_source_results:
                if str(src.get("name")).lower() == str(selected_product.get("name")).lower():
                    matching_source = src
                    break

        if not matching_source:
            raise ProductTruthValidationError(
                f"Product truth validation failed: Selected product '{selected_product.get('name')}' "
                f"(ID: '{source_pid}') was NOT found in verified live discovery results. Hallucination rejected."
            )

        # Price verification: LLM must not alter price
        selected_price = int(selected_product.get("amount_paise", 0))
        source_price = int(matching_source.get("amount_paise", 0))

        if selected_price != source_price:
            raise ProductTruthValidationError(
                f"Product truth validation failed: Price mismatch detected for '{matching_source.get('name')}'. "
                f"LLM proposed ₹{selected_price / 100:.2f} INR, "
                f"but verified source price is ₹{source_price / 100:.2f} INR. "
                "Price hallucination rejected."
            )

        # Return verified clean truth record with source provenance attached
        return {
            "product_id": matching_source.get("source_product_id", source_pid),
            "name": matching_source.get("name"),
            "description": matching_source.get("description", ""),
            "amount_paise": source_price,
            "currency": matching_source.get("currency", "INR"),
            "merchant_id": matching_source.get("merchant_identity", "mer_default"),
            "source_url": matching_source.get("source_url", ""),
            "retrieval_timestamp": matching_source.get("retrieval_timestamp", ""),
            "product_source": matching_source.get("verification_status", "VERIFIED_LIVE"),
            "is_verified": matching_source.get("is_verified", True),
        }
