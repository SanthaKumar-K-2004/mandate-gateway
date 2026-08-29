"""
M14 Integration Tests — Cross-Merchant Isolation & Resource Boundaries
"""

import unittest
from apps.api.domain.identity import AuthenticatedPrincipal, validate_merchant_access


class TestM14TenantIsolation(unittest.TestCase):
    """Test tenant isolation across resources (mandates, transactions, receipts, audit logs)."""

    def setUp(self) -> None:
        self.merchant_a_principal = AuthenticatedPrincipal(
            credential_id="cred_mer_a",
            merchant_id="mer_tenant_a",
            scopes={"payments:read", "payments:write"},
        )
        self.merchant_b_principal = AuthenticatedPrincipal(
            credential_id="cred_mer_b",
            merchant_id="mer_tenant_b",
            scopes={"payments:read", "payments:write"},
        )

    def test_merchant_a_accessing_merchant_a_resource_succeeds(self) -> None:
        validate_merchant_access(self.merchant_a_principal, "mer_tenant_a")

    def test_merchant_a_accessing_merchant_b_resource_fails(self) -> None:
        with self.assertRaises(PermissionError) as ctx:
            validate_merchant_access(self.merchant_a_principal, "mer_tenant_b")
        self.assertIn("Cross-tenant access denied", str(ctx.exception))

    def test_merchant_b_accessing_merchant_a_resource_fails(self) -> None:
        with self.assertRaises(PermissionError) as ctx:
            validate_merchant_access(self.merchant_b_principal, "mer_tenant_a")
        self.assertIn("Cross-tenant access denied", str(ctx.exception))

    def test_empty_target_merchant_id_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_merchant_access(self.merchant_a_principal, "")


if __name__ == "__main__":
    unittest.main()
