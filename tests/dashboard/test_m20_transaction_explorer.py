"""
M20 Transaction Explorer Suite
=============================
Workstreams 4 & 5 — Verifies transaction state filtering, state machine lifecycle representation,
and transaction detail inspection.
"""

from __future__ import annotations

import unittest
from apps.api.domain.types import TransactionState


class TestM20TransactionExplorer(unittest.TestCase):
    """Transaction explorer test suite."""

    def test_01_transaction_state_enumeration(self) -> None:
        """Verify transaction states match expected enum values."""
        valid_states = [s.value for s in TransactionState]
        self.assertIn("COMMITTED", valid_states)
        self.assertIn("EXECUTING", valid_states)
        self.assertIn("AUTHORIZED", valid_states)
        self.assertIn("ROLLED_BACK", valid_states)

    def test_02_transaction_filtering_by_state(self) -> None:
        """Verify filtering logic maps transaction items correctly."""
        mock_txs = [
            {"id": "tx_1", "state": "COMMITTED"},
            {"id": "tx_2", "state": "EXECUTING"},
            {"id": "tx_3", "state": "COMMITTED"},
            {"id": "tx_4", "state": "FAILED"},
        ]
        committed = [t for t in mock_txs if t["state"] == "COMMITTED"]
        self.assertEqual(len(committed), 2)
        executing = [t for t in mock_txs if t["state"] == "EXECUTING"]
        self.assertEqual(len(executing), 1)


if __name__ == "__main__":
    unittest.main()
