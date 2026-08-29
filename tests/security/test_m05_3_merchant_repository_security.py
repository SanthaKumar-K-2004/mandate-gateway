"""
Security tests for S05.3.2 MerchantRepository.
"""

from __future__ import annotations

import unittest
from db.repository.merchant_repository import MerchantRepository


class TestMerchantRepositorySecurity(unittest.TestCase):
    """Security test suite for MerchantRepository."""

    FORBIDDEN_MUTATION_METHODS = [
        "update",
        "delete",
        "update_merchant",
        "delete_merchant",
        "delete_policy",
        "delete_product",
        "update_policy",
        "commit",
        "execute_raw",
    ]

    def test_no_unsafe_mutation_methods_exposed(self) -> None:
        """Verify MerchantRepository exposes no generic update or delete methods."""
        for method_name in self.FORBIDDEN_MUTATION_METHODS:
            self.assertFalse(
                hasattr(MerchantRepository, method_name),
                f"Forbidden security-bypassing method '{method_name}' exposed on MerchantRepository!",
            )

    def test_explicit_public_api_surface(self) -> None:
        """Verify MerchantRepository only exposes intentional domain methods."""
        public_methods = [m for m in dir(MerchantRepository) if not m.startswith("_")]
        allowed_methods = {
            "get_by_id",
            "session",
            "model_cls",
            "create_merchant",
            "get_merchant_by_account",
            "create_policy",
            "get_active_policy",
            "get_policy_by_version",
            "create_product",
            "get_product",
            "list_products",
        }
        unexpected = set(public_methods) - allowed_methods
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected public methods on MerchantRepository: {unexpected}",
        )


if __name__ == "__main__":
    unittest.main()
