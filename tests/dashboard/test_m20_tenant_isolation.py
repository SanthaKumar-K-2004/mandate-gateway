"""
M20 Dashboard Multi-Tenant Isolation & Security Suite
=====================================================
Workstream 11 — Verifies multi-tenant isolation, cross-merchant resource access rejection,
and IDOR prevention across dashboard control plane endpoints.
"""

from __future__ import annotations

import unittest
from apps.api.domain.identity import AuthenticatedPrincipal, validate_merchant_access


class TestM20TenantIsolation(unittest.TestCase):
    """Multi-tenant isolation and IDOR rejection suite for M20 dashboard."""

    def test_01_same_tenant_access_allowed(self) -> None:
        """Verify principal can access resources bound to its own merchant ID."""
        principal = AuthenticatedPrincipal(
            credential_id="cred_merchant_a",
            merchant_id="mer_tenant_alpha",
            scopes={"merchant:read", "transaction:read"},
        )
        # Same merchant ID -> Must pass without raising PermissionError
        validate_merchant_access(principal, "mer_tenant_alpha")

    def test_02_cross_merchant_access_denied(self) -> None:
        """Verify principal attempting cross-merchant access raises PermissionError."""
        principal = AuthenticatedPrincipal(
            credential_id="cred_merchant_a",
            merchant_id="mer_tenant_alpha",
            scopes={"merchant:read", "transaction:read"},
        )
        with self.assertRaises(PermissionError):
            validate_merchant_access(principal, "mer_tenant_beta")

    def test_03_admin_override_scope(self) -> None:
        """Verify admin or wildcard scope allows administrative multi-tenant inspection."""
        principal = AuthenticatedPrincipal(
            credential_id="cred_admin_01",
            merchant_id="mer_operator",
            scopes={"*"},
        )
        # Wildcard scope allows cross-merchant inspection for operator tools
        validate_merchant_access(principal, "mer_tenant_beta")


if __name__ == "__main__":
    unittest.main()
