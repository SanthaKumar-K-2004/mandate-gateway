"""
Unit tests for End-to-End Live Agent Commerce Pilot (M26).
"""

from __future__ import annotations

import unittest

from scripts.run_live_commerce_pilot import run_live_commerce_pilot


class TestLiveCommercePilot(unittest.TestCase):
    """End-to-End Live Commerce Pilot test suite."""

    def test_01_run_live_pilot(self) -> None:
        """Verify 10-stage end-to-end live commerce pilot completes cleanly."""
        res = run_live_commerce_pilot()
        self.assertEqual(res, 0)
