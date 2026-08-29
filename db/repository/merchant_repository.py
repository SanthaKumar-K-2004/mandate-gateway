"""
S05.3.2 — Merchant Repository.

Domain persistence repository for Merchant identities, policies, and products.
"""

from __future__ import annotations

import json
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.merchant import MerchantModel
from db.models.policy import MerchantPolicyModel
from db.models.product import ProductModel
from db.repository.base import BaseRepository


class MerchantRepository(BaseRepository[MerchantModel]):
    """
    Repository for managing Merchant entities, versioned policies, and catalog products.

    Transaction Governance:
      - Repository methods flush mutations to the underlying session to trigger database
        constraints (uniqueness, check constraints, foreign keys) without committing.
      - Commit and rollback operations are explicitly controlled by transaction orchestrators.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MerchantModel, session)

    async def create_merchant(
        self,
        merchant_id: str,
        name: str,
        razorpay_account_id: str | None = None,
        active: bool = True,
    ) -> MerchantModel:
        """Create and persist a new merchant identity."""
        merchant = MerchantModel(
            merchant_id=merchant_id,
            name=name,
            razorpay_account_id=razorpay_account_id,
            active=active,
        )
        self._session.add(merchant)
        await self._session.flush()
        return merchant

    async def get_merchant_by_account(self, razorpay_account_id: str) -> MerchantModel | None:
        """Retrieve a merchant by its unique Razorpay account ID."""
        stmt = select(MerchantModel).where(MerchantModel.razorpay_account_id == razorpay_account_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_policy(
        self,
        policy_id: str,
        merchant_id: str,
        policy_version: str,
        autonomous_limit_paise: int,
        step_up_threshold_paise: int,
        allowed_categories: list[str] | None = None,
        allowed_operations: list[str] | None = None,
        blocked_operations: list[str] | None = None,
        active: bool = True,
    ) -> MerchantPolicyModel:
        """Create and persist a versioned merchant policy."""
        allowed_cats_str = json.dumps(allowed_categories or [])
        allowed_ops_str = json.dumps(allowed_operations or [])
        blocked_ops_str = json.dumps(blocked_operations or [])

        policy = MerchantPolicyModel(
            id=policy_id,
            merchant_id=merchant_id,
            policy_version=policy_version,
            autonomous_limit_paise=autonomous_limit_paise,
            step_up_threshold_paise=step_up_threshold_paise,
            allowed_categories_json=allowed_cats_str,
            allowed_operations_json=allowed_ops_str,
            blocked_operations_json=blocked_ops_str,
            active=active,
        )
        self._session.add(policy)
        await self._session.flush()
        return policy

    async def get_active_policy(self, merchant_id: str) -> MerchantPolicyModel | None:
        """Retrieve the currently active policy for a merchant."""
        stmt = (
            select(MerchantPolicyModel)
            .where(
                MerchantPolicyModel.merchant_id == merchant_id,
                MerchantPolicyModel.active.is_(True),
            )
            .order_by(MerchantPolicyModel.effective_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_policy_by_version(
        self, merchant_id: str, policy_version: str
    ) -> MerchantPolicyModel | None:
        """Retrieve a specific policy version for a merchant."""
        stmt = select(MerchantPolicyModel).where(
            MerchantPolicyModel.merchant_id == merchant_id,
            MerchantPolicyModel.policy_version == policy_version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_product(
        self,
        product_id: str,
        merchant_id: str,
        name: str,
        price_paise: int,
        category: str,
        currency: str = "INR",
        description: str | None = None,
        active: bool = True,
    ) -> ProductModel:
        """Create and persist a catalog product for a merchant."""
        product = ProductModel(
            product_id=product_id,
            merchant_id=merchant_id,
            name=name,
            price_paise=price_paise,
            category=category,
            currency=currency,
            description=description,
            active=active,
        )
        self._session.add(product)
        await self._session.flush()
        return product

    async def get_product(self, product_id: str) -> ProductModel | None:
        """Retrieve a catalog product by ID."""
        return await self._session.get(ProductModel, product_id)

    async def list_products(
        self, merchant_id: str, active_only: bool = True
    ) -> Sequence[ProductModel]:
        """List catalog products for a merchant."""
        stmt = select(ProductModel).where(ProductModel.merchant_id == merchant_id)
        if active_only:
            stmt = stmt.where(ProductModel.active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalars().all()
