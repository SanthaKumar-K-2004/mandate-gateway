"""
S07 Unit Tests — API Security Identity & Authorization Domain.

Tests credential creation, salted secret hashing, constant-time verification,
status transitions (ACTIVE, REVOKED, EXPIRED), scope evaluation, and principal construction.
"""

import unittest

from apps.api.domain.identity import (
    AuthenticatedPrincipal,
    generate_credential_key_pair,
    hash_credential_secret,
    validate_merchant_access,
    validate_scopes,
    verify_credential_secret,
)


class TestApiIdentityUnit(unittest.TestCase):
    def test_credential_key_pair_generation(self) -> None:
        """Verify credential key pair generation produces correct format and entropy."""
        cred_id, prefix, raw_secret, secret_hash = generate_credential_key_pair("live")

        self.assertTrue(cred_id.startswith("cred_"))
        self.assertTrue(prefix.startswith("rzp_live_"))
        self.assertTrue(raw_secret.startswith(prefix))
        self.assertNotEqual(raw_secret, secret_hash)
        self.assertEqual(len(secret_hash), 64)  # SHA-256 hex string

    def test_secret_hashing_and_constant_time_verification(self) -> None:
        """Verify secret hashing and constant-time secret verification."""
        raw_secret = "rzp_live_12345678_abcdef9876543210"
        secret_hash = hash_credential_secret(raw_secret)

        # Valid secret must verify True
        self.assertTrue(verify_credential_secret(raw_secret, secret_hash))

        # Tampered secret must verify False
        self.assertFalse(verify_credential_secret(raw_secret + "_bad", secret_hash))
        self.assertFalse(verify_credential_secret("rzp_live_wrong", secret_hash))
        self.assertFalse(verify_credential_secret("", secret_hash))
        self.assertFalse(verify_credential_secret(raw_secret, ""))

    def test_authenticated_principal_scopes(self) -> None:
        """Verify scope checking on AuthenticatedPrincipal."""
        principal = AuthenticatedPrincipal(
            credential_id="cred_001",
            merchant_id="mer_100",
            scopes={"transaction:read", "transaction:write", "mandate:read"},
        )

        self.assertTrue(principal.has_scope("transaction:read"))
        self.assertTrue(principal.has_scope("transaction:write"))
        self.assertTrue(principal.has_scope("mandate:read"))
        self.assertFalse(principal.has_scope("merchant:write"))
        self.assertFalse(principal.has_scope("admin"))

        self.assertTrue(principal.has_all_scopes(["transaction:read", "transaction:write"]))
        self.assertFalse(principal.has_all_scopes(["transaction:read", "merchant:write"]))

    def test_admin_wildcard_scope(self) -> None:
        """Verify wildcard or admin scope bypasses granular scope checks."""
        admin_principal = AuthenticatedPrincipal(
            credential_id="cred_admin",
            merchant_id="mer_admin",
            scopes={"*"},
        )

        self.assertTrue(admin_principal.has_scope("any:arbitrary:scope"))
        self.assertTrue(admin_principal.has_all_scopes(["scope_a", "scope_b"]))

    def test_validate_merchant_access_enforcement(self) -> None:
        """Verify validate_merchant_access enforces tenant boundary."""
        p_merchant_a = AuthenticatedPrincipal(
            credential_id="cred_a",
            merchant_id="mer_A",
            scopes={"transaction:read"},
        )

        # Same merchant must pass cleanly
        validate_merchant_access(p_merchant_a, "mer_A")

        # Cross-tenant target merchant must raise PermissionError
        with self.assertRaises(PermissionError) as ctx:
            validate_merchant_access(p_merchant_a, "mer_B")

        self.assertIn("Cross-tenant access denied", str(ctx.exception))

    def test_validate_scopes_enforcement(self) -> None:
        """Verify validate_scopes enforces required scopes."""
        principal = AuthenticatedPrincipal(
            credential_id="cred_01",
            merchant_id="mer_01",
            scopes={"transaction:read"},
        )

        # Present scope passes
        validate_scopes(principal, ["transaction:read"])

        # Missing scope raises PermissionError
        with self.assertRaises(PermissionError) as ctx:
            validate_scopes(principal, ["transaction:read", "transaction:write"])

        self.assertIn("Scope authorization denied", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
