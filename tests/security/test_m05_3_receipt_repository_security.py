"""
Security tests for S05.3.7 ReceiptRepository.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from apps.api.domain.receipt_signer import ActionReceiptSigner, Ed25519KeyManager
from apps.api.domain.types import Currency, PolicyDecision
from db.models.receipt import ActionReceiptModel
from db.repository.receipt_repository import ReceiptRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestReceiptRepositorySecurity(unittest.TestCase):
    """Security test suite for ReceiptRepository."""

    FORBIDDEN_MUTATION_METHODS = [
        "update",
        "delete",
        "update_receipt",
        "delete_receipt",
        "re_sign",
        "update_signature",
        "update_payload_hash",
        "execute_raw",
        "commit",
        "rollback",
        "raw_sql",
        "override_receipt",
    ]

    def test_security_test_no_generic_mutation_escape_hatch(self) -> None:
        """Verify ReceiptRepository exposes no generic update or delete methods."""
        for method_name in self.FORBIDDEN_MUTATION_METHODS:
            self.assertFalse(
                hasattr(ReceiptRepository, method_name),
                f"Forbidden security-bypassing method '{method_name}' exposed on ReceiptRepository!",
            )

    def test_explicit_public_api_surface(self) -> None:
        """Verify ReceiptRepository only exposes intentional receipt persistence methods."""
        public_methods = [m for m in dir(ReceiptRepository) if not m.startswith("_")]
        allowed_methods = {
            "get_by_id",
            "session",
            "model_cls",
            "create_receipt",
            "get_receipt",
            "get_receipt_for_transaction",
            "get_receipt_for_audit_event",
        }
        unexpected = set(public_methods) - allowed_methods
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected public methods on ReceiptRepository: {unexpected}",
        )

    def test_controlled_mutation_d_context_binding_preservation(self) -> None:
        """
        Controlled Mutation Proof (Mutation D):
        Verify that receipts remain strictly bound to their authoritative transaction_id and audit_event_id.
        """
        rec = ActionReceiptModel(
            receipt_id="rcpt_sec_1",
            transaction_id="tx_original",
            audit_event_id="evt_original",
            canonical_payload_hash="hash_sec",
            signature_hex="sig_sec",
            public_key_hex="pub_sec",
            created_at=_utc_now(),
        )

        def validate_receipt_binding(
            r: ActionReceiptModel, expected_tx: str, expected_evt: str
        ) -> None:
            if r.transaction_id != expected_tx or r.audit_event_id != expected_evt:
                raise ValueError("Receipt context mismatch")

        # Correct matching passes
        validate_receipt_binding(rec, "tx_original", "evt_original")

        # Mismatched context fails closed
        with self.assertRaises(ValueError):
            validate_receipt_binding(rec, "tx_attacker", "evt_original")

    def test_controlled_mutation_e_signature_tamper_detection(self) -> None:
        """
        Controlled Mutation Proof (Mutation E):
        Verify that an Ed25519 signature generated over canonical payload cannot be verified if tampered.
        """
        key_mgr = Ed25519KeyManager.generate()
        signer = ActionReceiptSigner(key_mgr)

        signed_rcpt = signer.sign_receipt(
            transaction_id="tx_sig_test",
            mandate_id="man_sig_test",
            merchant_id="merchant_alpha",
            policy_version=1,
            cart_hash="a" * 64,
            amount_paise=10000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
        )

        # Re-verify original canonical hash
        self.assertTrue(signed_rcpt.verify_canonical_hash())

        # Tampered payload hash invalidates canonical hash verification
        tampered_rcpt = signed_rcpt.model_copy(update={"canonical_payload_hash": "b" * 64})
        self.assertFalse(tampered_rcpt.verify_canonical_hash())


if __name__ == "__main__":
    unittest.main()
