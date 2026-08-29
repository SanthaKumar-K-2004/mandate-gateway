"""
S05.3.1 — Base Repository Foundation.

Base generic repository providing type-safe read access and enforcing
explicit transaction ownership across all domain repositories.
"""

from __future__ import annotations

from typing import Generic, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Base generic repository for SQLAlchemy ORM models.

    Design Principles:
      1. Explicit AsyncSession injection only — no hidden session creation.
      2. No generic mutation methods (update/delete) on the base class.
      3. No implicit commit operations — callers/coordinators manage transactions.
      4. Safe read-only helper primitives for get_by_id and entity lookup.
    """

    def __init__(self, model_cls: Type[ModelT], session: AsyncSession) -> None:
        if session is None:
            raise ValueError("AsyncSession must be explicitly provided to repository.")
        self._model_cls = model_cls
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Return the underlying AsyncSession instance."""
        return self._session

    @property
    def model_cls(self) -> Type[ModelT]:
        """Return the target ORM model class."""
        return self._model_cls

    async def get_by_id(self, entity_id: str) -> ModelT | None:
        """
        Fetch a single entity by its primary key ID.

        Returns None if no matching entity exists.
        """
        result = await self._session.get(self._model_cls, entity_id)
        return result
