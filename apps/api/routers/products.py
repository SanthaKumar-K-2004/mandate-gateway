"""
S03.1 — Product Catalog API Router.

Implements REST API endpoints for catalog product management (Section 28, PROJECT_CONTEXT.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
import uuid

from apps.api.contracts.product import (
    ProductCreateRequest,
    ProductListResponse,
    ProductResponse,
)

try:
    from fastapi import APIRouter, HTTPException, status

    HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    HAS_FASTAPI = False
    APIRouter = Any  # type: ignore[misc,assignment]

    class status:  # type: ignore[no-redef]
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_404_NOT_FOUND = 404
        HTTP_400_BAD_REQUEST = 400

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail


# In-memory store for products
_PRODUCTS: dict[str, ProductResponse] = {}


if HAS_FASTAPI:
    products_router: Any = APIRouter(prefix="/api", tags=["Catalog Product Management"])
else:

    class DummyRouter:
        def post(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

        def get(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator

    products_router: Any = DummyRouter()  # type: ignore[no-redef]


@products_router.post(
    "/merchants/{merchant_id}/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(merchant_id: str, payload: ProductCreateRequest) -> ProductResponse:
    """Create a catalog product under a merchant."""
    product_id = f"prd_{uuid.uuid4().hex[:12]}"
    product = ProductResponse(
        product_id=product_id,
        merchant_id=merchant_id,
        name=payload.name,
        category=payload.category.lower(),
        price_paise=payload.price_paise,
        currency=payload.currency,
        description=payload.description,
        stock_quantity=payload.stock_quantity,
        created_at=datetime.now(timezone.utc),
    )
    _PRODUCTS[product_id] = product
    return product


@products_router.get(
    "/merchants/{merchant_id}/products",
    response_model=ProductListResponse,
)
def list_merchant_products(merchant_id: str) -> ProductListResponse:
    """List all catalog products for a merchant."""
    merchant_products = [p for p in _PRODUCTS.values() if p.merchant_id == merchant_id]
    return ProductListResponse(
        merchant_id=merchant_id,
        products=merchant_products,
        total_count=len(merchant_products),
    )


@products_router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
)
def get_product(product_id: str) -> ProductResponse:
    """Fetch product by ID."""
    if product_id not in _PRODUCTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found.",
        )
    return _PRODUCTS[product_id]
