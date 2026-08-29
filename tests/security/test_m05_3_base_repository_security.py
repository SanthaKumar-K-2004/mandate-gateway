"""
Security tests for S05.3.1 BaseRepository foundation.
"""

from __future__ import annotations

import unittest
from db.repository.base import BaseRepository


class TestBaseRepositorySecurity(unittest.TestCase):
    """Security test suite verifying no unsafe generic mutation APIs exist on BaseRepository."""

    FORBIDDEN_ATTRIBUTES = [
        "update",
        "delete",
        "update_anything",
        "delete_anything",
        "execute_raw",
        "raw_sql",
        "commit",
        "rollback",
        "save",
        "remove",
    ]

    def test_forbidden_mutation_apis_absent(self) -> None:
        """Verify that BaseRepository exposes no generic mutation or transaction commitment methods."""
        for attr in self.FORBIDDEN_ATTRIBUTES:
            self.assertFalse(
                hasattr(BaseRepository, attr),
                f"Forbidden generic attribute/method '{attr}' found on BaseRepository!",
            )

    def test_only_safe_public_methods(self) -> None:
        """Verify that BaseRepository only exposes approved safe methods/properties."""
        public_methods = [m for m in dir(BaseRepository) if not m.startswith("_")]
        expected_allowed = {"get_by_id", "session", "model_cls"}
        unexpected = set(public_methods) - expected_allowed
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected public attributes/methods on BaseRepository: {unexpected}",
        )


if __name__ == "__main__":
    unittest.main()
