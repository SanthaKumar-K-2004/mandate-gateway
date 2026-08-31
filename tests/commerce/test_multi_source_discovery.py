"""
Unit tests for Multi-Source Product Discovery Engine (M27).
"""

from __future__ import annotations

import unittest

from apps.api.commerce.multi_source_discovery import MultiSourceDiscoveryEngine


class TestMultiSourceDiscovery(unittest.TestCase):
    """MultiSourceDiscoveryEngine test suite."""

    def test_01_discover_candidates_success(self) -> None:
        """Verify candidate discovery across multiple sources."""
        engine = MultiSourceDiscoveryEngine()
        candidates, status = engine.discover_candidates(query="coffee", max_price_paise=20000)

        self.assertEqual(status, "SUCCESS")
        self.assertGreaterEqual(len(candidates), 2)

        for c in candidates:
            self.assertIsNotNone(c.product_id)
            self.assertIsNotNone(c.product_url)
            self.assertLessEqual(c.price_paise, 20000)

    def test_02_discover_candidates_budget_exceeded(self) -> None:
        """Verify no candidates returned if max price is set too low."""
        engine = MultiSourceDiscoveryEngine()
        candidates, status = engine.discover_candidates(query="coffee", max_price_paise=1000)

        self.assertEqual(status, "NO_MATCHING_PRODUCTS_FOUND")
        self.assertEqual(len(candidates), 0)
