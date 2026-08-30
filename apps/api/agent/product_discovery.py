"""
Mandate Gateway — Live Product Discovery Provider Abstraction
Workstream 3 — Provider abstraction retrieving real external commerce data.
Each result preserves source URL, retrieval timestamp, merchant identity, and verification status.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List


class ProductDiscoveryError(RuntimeError):
    """Raised when product discovery provider operations fail."""

    pass


class ProductDiscoveryProvider(abc.ABC):
    """Abstract base class for all product discovery providers."""

    @abc.abstractmethod
    def search_live_products(
        self, query: str, max_price_paise: int = 50000, category: str = "general"
    ) -> List[Dict[str, Any]]:
        """Search live external product data sources."""
        pass


class LiveProductSearchProvider(ProductDiscoveryProvider):
    """
    Production Live Product Discovery Provider.
    Queries real external open commerce APIs / public product endpoints via LiveDataOrchestrator.
    Normalizes results and attaches source URL, retrieval timestamp, and verification status.
    """

    def __init__(self) -> None:
        from apps.api.agent.live_data import LiveDataOrchestrator

        self.orchestrator = LiveDataOrchestrator()

    def search_live_products(
        self, query: str, max_price_paise: int = 50000, category: str = "general"
    ) -> List[Dict[str, Any]]:
        """Query real external product discovery API via LiveDataOrchestrator."""
        return self.orchestrator.search_live_products(query=query, max_price_paise=max_price_paise)
