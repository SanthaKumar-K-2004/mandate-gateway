"""
M14 Unit Tests — Core Security, Identity Hardening & Constant-Time Secret Verification
"""

import unittest

from apps.api.domain.identity import (
    AuthenticatedPrincipal,
    compute_credential_fingerprint,
    hash_credential_secret,
    verify_credential_secret,
    validate_merchant_access,
    validate_scopes,
)


class TestM14SecurityCore(unittest.TestCase):
    """Test identity hardening, constant-time secret comparison, fingerprinting, and scope validation."""

    def test_constant_time_secret_verification(self) -> None:
        raw_secret = "rzp_live_abcd1234_secret_entropy_5678"
        stored_hash = hash_credential_secret(raw_secret)

        self.assertTrue(verify_credential_secret(raw_secret, stored_hash))
        self.assertFalse(verify_credential_secret("wrong_secret", stored_hash))
        self.assertFalse(verify_credential_secret("", stored_hash))

    def test_credential_fingerprint_never_exposes_raw_key(self) -> None:
        raw_secret = "rzp_live_abcd1234_secret_entropy_5678"
        fp = compute_credential_fingerprint(raw_secret)

        self.assertTrue(fp.startswith("fp_rzp_"))
        self.assertNotIn(raw_secret, fp)
        self.assertNotIn("secret", fp)
        self.assertEqual(len(fp), 7 + 16)  # fp_rzp_ + 16 hex chars

    def test_tenant_isolation_validation(self) -> None:
        principal = AuthenticatedPrincipal(
            credential_id="cred_m1",
            merchant_id="mer_tenant_a",
            scopes={"payments:read"},
        )

        # Same merchant ID: passes cleanly
        validate_merchant_access(principal, "mer_tenant_a")

        # Cross-tenant access attempt: raises PermissionError
        with self.assertRaises(PermissionError) as ctx:
            validate_merchant_access(principal, "mer_tenant_b")
        self.assertIn("Cross-tenant access denied", str(ctx.exception))

    def test_admin_scope_tenant_override(self) -> None:
        admin_principal = AuthenticatedPrincipal(
            credential_id="cred_admin",
            merchant_id="mer_platform",
            scopes={"admin"},
        )

        # Admin principal can access any tenant resource
        validate_merchant_access(admin_principal, "mer_tenant_b")

    def test_scope_validation(self) -> None:
        principal = AuthenticatedPrincipal(
            credential_id="cred_123",
            merchant_id="mer_123",
            scopes={"payments:read", "payments:write"},
        )

        validate_scopes(principal, ["payments:read"])
        validate_scopes(principal, ["payments:read", "payments:write"])

        with self.assertRaises(PermissionError) as ctx:
            validate_scopes(principal, ["admin:manage"])
        self.assertIn("Scope authorization denied", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
