"""
S03.1 — Product Catalog API Response Contracts.

Response schemas for `/api/merchants/{id}/products` and `/api/products/{id}` endpoints (Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from apps.api.domain.types import Currency


class ProductCreateRequest(BaseModel):
    """Request payload to register a product under a merchant catalog."""

    name: str = Field(..., min_length=1, max_length=500, description="Product display name.")
    category: str = Field(..., min_length=1, max_length=100, description="Product category.")
    price_paise: int = Field(..., ge=0, description="Unit price in paise.")
    currency: Currency = Field(default=Currency.INR, description="Product currency.")
    description: str | None = Field(
        default=None, max_length=2000, description="Optional product description."
    )
    stock_quantity: int = Field(default=100, ge=0, description="Available stock quantity.")


class ProductResponse(BaseModel):
    """Response DTO representing a catalog product."""

    product_id: str
    merchant_id: str
    name: str
    category: str
    price_paise: int
    currency: Currency
    description: str | None = None
    stock_quantity: int
    created_at: datetime


class ProductListResponse(BaseModel):
    """Response DTO for listing merchant products."""

    model_config = {"extra": "forbid"}

    merchant_id: str
    products: list[ProductResponse]
    total_count: int
