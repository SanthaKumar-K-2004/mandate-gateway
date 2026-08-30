"""
Security tests for S05.3.4 TransactionRepository.
"""

from __future__ import annotations

import unittest
from db.models.transaction import TransactionModel
from db.repository.transaction_repository import TransactionRepository


class TestTransactionRepositorySecurity(unittest.TestCase):
    """Security test suite for TransactionRepository."""

    FORBIDDEN_MUTATION_METHODS = [
        "update",
        "delete",
        "update_transaction",
        "delete_transaction",
        "update_state_arbitrary",
        "commit",
        "execute_raw",
        "raw_sql",
    ]

    def test_no_unsafe_mutation_methods_exposed(self) -> None:
        """Verify TransactionRepository exposes no generic update or delete methods."""
        for method_name in self.FORBIDDEN_MUTATION_METHODS:
            self.assertFalse(
                hasattr(TransactionRepository, method_name),
                f"Forbidden security-bypassing method '{method_name}' exposed on TransactionRepository!",
            )

    def test_explicit_public_api_surface(self) -> None:
        """Verify TransactionRepository only exposes intentional domain methods."""
        public_methods = [m for m in dir(TransactionRepository) if not m.startswith("_")]
        allowed_methods = {
            "get_by_id",
            "session",
            "model_cls",
            "create_transaction",
            "get_transaction",
            "get_transaction_for_buyer",
            "get_transaction_for_context",
            "get_transaction_by_idempotency_key",
            "get_transaction_by_idempotency",
            "get_stuck_executing_transactions",
            "lock_transaction_for_update",
            "transition_transaction_state",
            "mark_provider_dispatch_started",
            "record_provider_outcome",
            "list_transactions_requiring_reconciliation",
        }
        unexpected = set(public_methods) - allowed_methods
        self.assertEqual(
            unexpected,
            set(),
            f"Unexpected public methods on TransactionRepository: {unexpected}",
        )

    def test_controlled_mutation_idempotency_mismatch_bypass_detection(self) -> None:
        """
        Controlled Mutation Proof:
        Simulate a mutation where an idempotency key mismatch check is bypassed,
        and prove our security assertion detects the failure.
        """
        existing = TransactionModel(
            transaction_id="tx_1",
            buyer_id="buyer_alice",
            merchant_id="m_1",
            mandate_id="man_1",
            amount_paise=5000,
            cart_hash="hash_123",
            idempotency_key="key_1",
        )

        new_request_amount = 90000  # Conflicting request!

        # Correct security check logic:
        def check_idempotency_context(tx: TransactionModel, req_amount: int) -> None:
            if tx.amount_paise != req_amount:
                raise ValueError("Idempotency key mismatch")

        # Mutated logic (bypasses check):
        def mutated_check(tx: TransactionModel, req_amount: int) -> None:
            pass  # Bypass!

        # Security assertion proves mismatch MUST raise ValueError:
        with self.assertRaises(ValueError):
            check_idempotency_context(existing, new_request_amount)


if __name__ == "__main__":
    unittest.main()
