"""
S02.6 — Action Receipt Cryptography & Offline Verification Unit Tests.

Tests Ed25519 key management, action receipt RFC 8785 canonical digest signing,
and 5-point offline receipt verification.
"""

import hashlib
import unittest

from apps.api.domain.audit_ledger import AuditLedger
from apps.api.domain.receipt_signer import ActionReceiptSigner, Ed25519KeyManager
from apps.api.domain.receipt_verifier import ReceiptVerifier
from apps.api.domain.types import AuditEventType, Currency, PolicyDecision


class TestReceiptCrypto(unittest.TestCase):
    def setUp(self) -> None:
        self.key_manager = Ed25519KeyManager.generate()
        self.signer = ActionReceiptSigner(self.key_manager)
        self.sample_cart_hash = hashlib.sha256(b"canonical_cart_items").hexdigest()

    def test_key_manager_export_import(self) -> None:
        """Verify Ed25519 key serialization to/from hex and base64."""
        priv_hex = self.key_manager.get_private_key_hex()
        pub_hex = self.key_manager.get_public_key_hex()
        pub_b64 = self.key_manager.get_public_key_base64()

        reloaded_km = Ed25519KeyManager.from_private_key_hex(priv_hex)
        self.assertEqual(reloaded_km.get_public_key_hex(), pub_hex)

        reloaded_pub_b64 = Ed25519KeyManager.load_public_key_base64(pub_b64)
        reloaded_pub_hex = Ed25519KeyManager.load_public_key_hex(pub_hex)

        self.assertIsNotNone(reloaded_pub_b64)
        self.assertIsNotNone(reloaded_pub_hex)

    def test_sign_receipt_and_verify(self) -> None:
        """Verify creating signed ActionReceipt and performing 5-point offline verification."""
        receipt = self.signer.sign_receipt(
            transaction_id="tx_12345",
            mandate_id="mandate_789",
            merchant_id="merchant_acme",
            policy_version=1,
            cart_hash=self.sample_cart_hash,
            amount_paise=299900,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
            execution_tool="create_order",
            execution_reference="order_98765",
            audit_hash=hashlib.sha256(b"audit_event_hash").hexdigest(),
        )

        self.assertIsNotNone(receipt.signature)
        self.assertEqual(len(receipt.canonical_payload_hash), 64)
        self.assertTrue(receipt.verify_canonical_hash())

        # Verify offline with ReceiptVerifier
        result = ReceiptVerifier.verify(
            receipt=receipt,
            public_key=self.key_manager.public_key,
            expected_transaction_id="tx_12345",
            expected_mandate_id="mandate_789",
            expected_merchant_id="merchant_acme",
            expected_amount_paise=299900,
            expected_cart_hash=self.sample_cart_hash,
            expected_currency=Currency.INR,
            expected_decision=PolicyDecision.ALLOW,
        )

        self.assertTrue(result.is_valid)
        self.assertTrue(result.canonical_payload_valid)
        self.assertTrue(result.signature_valid)
        self.assertTrue(result.structure_valid)
        self.assertTrue(result.binding_valid)
        self.assertIn("VALID RECEIPT", result.summary())

    def test_verify_with_pubkey_hex_and_b64(self) -> None:
        """Verify verifier accepts public key as hex and base64 strings."""
        receipt = self.signer.sign_receipt(
            transaction_id="tx_100",
            mandate_id="man_100",
            merchant_id="merch_100",
            policy_version=1,
            cart_hash=self.sample_cart_hash,
            amount_paise=5000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
        )

        # Hex verification
        res_hex = ReceiptVerifier.verify(
            receipt=receipt,
            public_key=self.key_manager.get_public_key_hex(),
        )
        self.assertTrue(res_hex.is_valid)

        # Base64 verification
        res_b64 = ReceiptVerifier.verify(
            receipt=receipt,
            public_key=self.key_manager.get_public_key_base64(),
        )
        self.assertTrue(res_b64.is_valid)

    def test_verify_audit_linkage(self) -> None:
        """Verify action receipt audit_hash linkage against live AuditLedger."""
        ledger = AuditLedger()
        ledger.append_event(
            event_type=AuditEventType.CART_PROPOSED,
            transaction_id="tx_audit_test",
        )
        event2 = ledger.append_event(
            event_type=AuditEventType.PAYMENT_SUCCESS,
            transaction_id="tx_audit_test",
        )

        receipt = self.signer.sign_receipt(
            transaction_id="tx_audit_test",
            mandate_id="m_1",
            merchant_id="merch_1",
            policy_version=1,
            cart_hash=self.sample_cart_hash,
            amount_paise=1000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
            audit_hash=event2.event_hash,
        )

        # Verification with ledger
        res = ReceiptVerifier.verify(
            receipt=receipt,
            public_key=self.key_manager.public_key,
            audit_ledger=ledger,
        )
        self.assertTrue(res.is_valid)
        self.assertTrue(res.audit_link_valid)


if __name__ == "__main__":
    unittest.main()
