"""
S02.6 — Audit Ledger & Action Receipt End-to-End Integration Tests.

Verifies end-to-end transaction lifecycle event recording, ledger chain
verification, Ed25519 receipt generation, and offline CLI verification.
"""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from apps.api.domain.audit_ledger import AuditLedger
from apps.api.domain.receipt_signer import ActionReceiptSigner, Ed25519KeyManager
from apps.api.domain.receipt_verifier import ReceiptVerifier
from apps.api.domain.types import AuditEventType, Currency, PolicyDecision


class TestAuditIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = AuditLedger()
        self.key_manager = Ed25519KeyManager.generate()
        self.signer = ActionReceiptSigner(self.key_manager)

    def test_full_transaction_audit_and_receipt_lifecycle(self) -> None:
        """Verify full lifecycle: mandate -> policy -> reservation -> execution -> audit -> receipt -> CLI verify."""
        transaction_id = "tx_e2e_999"
        mandate_id = "mandate_e2e_1"
        merchant_id = "merchant_razorpay_shop"
        buyer_id = "buyer_alice"
        cart_hash = hashlib.sha256(b"item_1:1000:item_2:2000").hexdigest()
        amount_paise = 300000

        # 1. Record transaction audit steps in AuditLedger
        self.ledger.append_event(
            event_type=AuditEventType.MANDATE_CREATED,
            mandate_id=mandate_id,
            buyer_id=buyer_id,
            payload={"limit_paise": 500000},
        )
        self.ledger.append_event(
            event_type=AuditEventType.CART_PROPOSED,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            payload={"cart_hash": cart_hash, "amount_paise": amount_paise},
        )
        self.ledger.append_event(
            event_type=AuditEventType.POLICY_EVALUATED,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            payload={"decision": "ALLOW"},
        )
        self.ledger.append_event(
            event_type=AuditEventType.RESERVATION_CREATED,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            payload={"reserved_paise": amount_paise},
        )
        self.ledger.append_event(
            event_type=AuditEventType.EXECUTION_AUTHORIZED,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            payload={"tool": "create_order"},
        )
        e_pay = self.ledger.append_event(
            event_type=AuditEventType.PAYMENT_SUCCESS,
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            payload={"razorpay_order_id": "order_RZP123456"},
        )

        # 2. Verify AuditLedger cryptographic chain integrity
        self.assertTrue(self.ledger.verify_chain()[0])
        self.assertEqual(self.ledger.count(), 6)

        # 3. Generate Ed25519-signed ActionReceipt linked to latest audit event
        receipt = self.signer.sign_receipt(
            transaction_id=transaction_id,
            mandate_id=mandate_id,
            merchant_id=merchant_id,
            policy_version=1,
            cart_hash=cart_hash,
            amount_paise=amount_paise,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
            execution_tool="create_order",
            execution_reference="order_RZP123456",
            audit_hash=e_pay.event_hash,
        )

        # 4. Verify receipt via ReceiptVerifier in Python
        verifier_res = ReceiptVerifier.verify(
            receipt=receipt,
            public_key=self.key_manager.public_key,
            expected_transaction_id=transaction_id,
            expected_mandate_id=mandate_id,
            expected_merchant_id=merchant_id,
            expected_amount_paise=amount_paise,
            expected_cart_hash=cart_hash,
            audit_ledger=self.ledger,
        )

        self.assertTrue(verifier_res.is_valid)
        self.assertTrue(verifier_res.audit_link_valid)

        # 5. Verify receipt via standalone CLI script `scripts/verify_receipt.py`
        receipt_dict = receipt.model_dump(mode="json")
        pubkey_hex = self.key_manager.get_public_key_hex()

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp_file:
            json.dump(receipt_dict, tmp_file, indent=2)
            tmp_path = tmp_file.name

        try:
            cli_cmd = [
                "python",
                "scripts/verify_receipt.py",
                tmp_path,
                "--public-key",
                pubkey_hex,
                "--expected-transaction-id",
                transaction_id,
            ]
            process = subprocess.run(cli_cmd, capture_output=True, text=True, check=False)
            self.assertEqual(
                process.returncode, 0, msg=f"CLI Output: {process.stdout} Error: {process.stderr}"
            )
            self.assertIn("VALID RECEIPT", process.stdout)
            self.assertIn("✓ Signature valid", process.stdout)
            self.assertIn("✓ Payload canonical", process.stdout)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
