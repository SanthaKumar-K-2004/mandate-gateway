"""
S04.4 — Unit Test Suite for Crash Consistency, Recovery & Reconciliation.

Verifies RecoveryReconciliationEngine unit behavior: stale transaction audit,
unknown-provider outcome handling (UNKNOWN != FAILURE / SUCCESS), budget reservation
recovery, and audit/receipt consistency cases.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from apps.api.domain.audit_ledger import AuditLedger
from apps.api.domain.budget_engine import BudgetEngine
from apps.api.domain.nonce_engine import NonceEngine
from apps.api.domain.receipt_signer import ActionReceiptSigner, Ed25519KeyManager
from apps.api.domain.reconciliation import RecoveryReconciliationEngine
from apps.api.domain.step_up_engine import StepUpEngine
from apps.api.domain.types import (
    AuditEventType,
    Currency,
    PaymentResultState,
    PolicyDecision,
    TransactionState,
)


class TestS044RecoveryUnit(unittest.TestCase):
    """Unit tests for S04.4 Crash Consistency & Recovery Engine."""

    def setUp(self) -> None:
        self.reconciliation_engine = RecoveryReconciliationEngine()
        self.budget_engine = BudgetEngine()
        self.nonce_engine = NonceEngine()
        self.step_up_engine = StepUpEngine()
        self.audit_ledger = AuditLedger()

    def test_stale_transactions_audit(self) -> None:
        """Verify transactions interrupted in non-terminal states past timeout are detected."""
        now = datetime.now(timezone.utc)
        stale_time = (now - timedelta(seconds=600)).isoformat()
        fresh_time = (now - timedelta(seconds=10)).isoformat()

        transactions = [
            {
                "transaction_id": "tx_stale_1",
                "mandate_id": "m_1",
                "merchant_id": "merch_1",
                "amount_paise": 1000,
                "state": TransactionState.EXECUTING.value,
                "updated_at": stale_time,
            },
            {
                "transaction_id": "tx_fresh_1",
                "mandate_id": "m_1",
                "merchant_id": "merch_1",
                "amount_paise": 1000,
                "state": TransactionState.EXECUTING.value,
                "updated_at": fresh_time,
            },
            {
                "transaction_id": "tx_completed_1",
                "mandate_id": "m_1",
                "merchant_id": "merch_1",
                "amount_paise": 1000,
                "state": TransactionState.COMPLETED.value,
                "updated_at": stale_time,
            },
        ]

        stale = self.reconciliation_engine.audit_stale_transactions(
            transactions, timeout_seconds=300, at=now
        )
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].transaction_id, "tx_stale_1")
        self.assertEqual(stale[0].state, TransactionState.EXECUTING)

    def test_reconcile_provider_unknown_prohibits_blind_retry(self) -> None:
        """Verify UNKNOWN provider state prohibits blind payment retries."""
        res = self.reconciliation_engine.reconcile_provider_unknown(
            transaction_id="tx_unk_1",
            provider_result_state=PaymentResultState.UNKNOWN,
        )
        self.assertFalse(res["reconciled"])
        self.assertFalse(res["retry_allowed"])
        self.assertEqual(res["decision"], PolicyDecision.REJECT.value)
        self.assertEqual(res["reason"], "PROVIDER_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED")

    def test_reconcile_provider_failed_allows_safe_retry(self) -> None:
        """Verify FAILED provider state permits safe retry."""
        res = self.reconciliation_engine.reconcile_provider_unknown(
            transaction_id="tx_fail_1",
            provider_result_state=PaymentResultState.FAILED,
        )
        self.assertTrue(res["reconciled"])
        self.assertTrue(res["retry_allowed"])
        self.assertEqual(res["decision"], PolicyDecision.REJECT.value)

    def test_audit_budget_reservations_releases_failed_tx_reservations(self) -> None:
        """Verify stranded reservations for failed transactions are safely released."""
        m_id = "mandate_rec_1"
        self.budget_engine.register_budget(m_id, daily_limit_paise=5000, currency=Currency.INR)
        self.budget_engine.reserve(m_id, "tx_failed_1", 2000, Currency.INR)

        transactions = [
            {
                "transaction_id": "tx_failed_1",
                "mandate_id": m_id,
                "amount_paise": 2000,
                "state": TransactionState.FAILURE.value,
            }
        ]

        orphaned = self.reconciliation_engine.audit_budget_reservations(
            self.budget_engine, transactions
        )
        self.assertEqual(len(orphaned), 1)
        self.assertTrue(orphaned[0].released)
        b = self.budget_engine.get_budget(m_id)
        self.assertIsNotNone(b)
        if b is not None:
            self.assertEqual(b.reserved_paise, 0)

    def test_audit_receipt_consistency_cases(self) -> None:
        """Verify audit receipt consistency cases B (receipt missing) and D (unknown provider)."""
        km = Ed25519KeyManager.generate()
        signer = ActionReceiptSigner(key_manager=km)

        rcpt = signer.sign_receipt(
            transaction_id="tx_ok_1",
            mandate_id="m_1",
            merchant_id="merch_1",
            policy_version=1,
            cart_hash="00" * 32,
            amount_paise=1000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
            execution_reference="ref_1",
            audit_hash="00" * 32,
        )

        transactions = [
            {
                "transaction_id": "tx_ok_1",
                "state": TransactionState.SUCCESS.value,
                "provider_outcome": PaymentResultState.SUCCESS.value,
            },
            {
                "transaction_id": "tx_no_receipt",
                "state": TransactionState.SUCCESS.value,
                "provider_outcome": PaymentResultState.SUCCESS.value,
            },
            {
                "transaction_id": "tx_unk_prov",
                "state": TransactionState.SUCCESS.value,
                "provider_outcome": PaymentResultState.UNKNOWN.value,
            },
        ]

        self.audit_ledger.append_event(
            AuditEventType.EXECUTION_AUTHORIZED,
            transaction_id="tx_ok_1",
        )

        inconsistencies = self.reconciliation_engine.audit_audit_receipt_consistency(
            self.audit_ledger, [rcpt], transactions
        )

        cases = {inc["case"] for inc in inconsistencies}
        self.assertIn("CASE_B_RECEIPT_MISSING", cases)
        self.assertIn("CASE_D_UNRESOLVED_UNKNOWN_PROVIDER", cases)


if __name__ == "__main__":
    unittest.main()
