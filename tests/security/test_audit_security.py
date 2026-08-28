"""
S02.6 — Audit Ledger & Action Receipt Security & Adversarial Tests.

Tests detection of audit chain tampering, event payload corruption, signature
forgery, public key mismatch, and context parameter tampering.
"""

import hashlib
import unittest

from apps.api.domain.audit import AuditEvent
from apps.api.domain.audit_ledger import AuditLedger
from apps.api.domain.receipt_signer import ActionReceiptSigner, Ed25519KeyManager
from apps.api.domain.receipt_verifier import ReceiptVerifier
from apps.api.domain.types import AuditEventType, Currency, PolicyDecision


class TestAuditSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = AuditLedger()
        self.key_manager = Ed25519KeyManager.generate()
        self.signer = ActionReceiptSigner(self.key_manager)
        self.sample_cart_hash = hashlib.sha256(b"cart_data").hexdigest()

    def test_audit_chain_payload_tampering_detected(self) -> None:
        """Verify modifying an event payload breaks verify_chain()."""
        self.ledger.append_event(AuditEventType.MANDATE_CREATED, mandate_id="m1")
        e2 = self.ledger.append_event(
            AuditEventType.CART_PROPOSED, transaction_id="tx1", payload={"price": 100}
        )
        self.ledger.append_event(AuditEventType.EXECUTION_AUTHORIZED, transaction_id="tx1")

        is_valid, err = self.ledger.verify_chain()
        self.assertTrue(is_valid)

        # Tamper with middle event in-place
        self.ledger._events[1] = AuditEvent(
            event_id=e2.event_id,
            event_type=e2.event_type,
            timestamp=e2.timestamp,
            transaction_id=e2.transaction_id,
            mandate_id=e2.mandate_id,
            merchant_id=e2.merchant_id,
            buyer_id=e2.buyer_id,
            payload={"price": 999999},  # Tampered payload!
            previous_hash=e2.previous_hash,
            event_hash=e2.event_hash,
        )

        is_valid_after, err_after = self.ledger.verify_chain()
        self.assertFalse(is_valid_after)
        self.assertIsNotNone(err_after)
        self.assertIn("Hash calculation invalid", str(err_after))

    def test_audit_chain_event_deletion_detected(self) -> None:
        """Verify deleting an event from the chain breaks verify_chain()."""
        self.ledger.append_event(AuditEventType.MANDATE_CREATED, mandate_id="m1")
        self.ledger.append_event(AuditEventType.CART_PROPOSED, transaction_id="tx1")
        self.ledger.append_event(AuditEventType.EXECUTION_AUTHORIZED, transaction_id="tx1")

        # Delete middle event
        del self.ledger._events[1]

        is_valid, err = self.ledger.verify_chain()
        self.assertFalse(is_valid)
        self.assertIn("Chain broken", str(err))

    def test_receipt_forged_signature_rejected(self) -> None:
        """Verify forged Ed25519 signature fails verification."""
        receipt = self.signer.sign_receipt(
            transaction_id="tx_security_1",
            mandate_id="mandate_1",
            merchant_id="merchant_1",
            policy_version=1,
            cart_hash=self.sample_cart_hash,
            amount_paise=50000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
        )

        # Replace signature with forged signature from another keypair
        other_signer = ActionReceiptSigner()
        forged_receipt = other_signer.sign_receipt(
            transaction_id="tx_security_1",
            mandate_id="mandate_1",
            merchant_id="merchant_1",
            policy_version=1,
            cart_hash=self.sample_cart_hash,
            amount_paise=50000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
            receipt_id=receipt.receipt_id,
        )

        # Verifying forged receipt against original public key MUST fail
        result = ReceiptVerifier.verify(
            receipt=forged_receipt,
            public_key=self.key_manager.public_key,
        )

        self.assertFalse(result.is_valid)
        self.assertFalse(result.signature_valid)
        self.assertIn("signature is invalid", str(result.error))

    def test_receipt_tampered_amount_rejected(self) -> None:
        """Verify modifying receipt amount invalidates canonical payload digest."""
        receipt = self.signer.sign_receipt(
            transaction_id="tx_security_2",
            mandate_id="mandate_1",
            merchant_id="merchant_1",
            policy_version=1,
            cart_hash=self.sample_cart_hash,
            amount_paise=1000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
        )

        # Modify amount in dump without re-signing
        tampered_dict = receipt.model_dump()
        tampered_dict["amount_paise"] = 999999  # Tampered amount!

        result = ReceiptVerifier.verify(
            receipt=tampered_dict,
            public_key=self.key_manager.public_key,
        )

        self.assertFalse(result.is_valid)
        self.assertFalse(result.canonical_payload_valid)
        self.assertIn("Canonical payload hash mismatch", str(result.error))

    def test_receipt_binding_mismatch_rejected(self) -> None:
        """Verify expected transaction binding mismatch is detected."""
        receipt = self.signer.sign_receipt(
            transaction_id="tx_security_3",
            mandate_id="mandate_real",
            merchant_id="merchant_real",
            policy_version=1,
            cart_hash=self.sample_cart_hash,
            amount_paise=5000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
        )

        result = ReceiptVerifier.verify(
            receipt=receipt,
            public_key=self.key_manager.public_key,
            expected_merchant_id="merchant_attacker",  # Mismatched expected merchant
        )

        self.assertFalse(result.is_valid)
        self.assertFalse(result.binding_valid)
        self.assertIn("Context binding verification failed", str(result.error))


if __name__ == "__main__":
    unittest.main()
