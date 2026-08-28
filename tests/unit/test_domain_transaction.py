"""
Unit tests for Transaction domain model & state machine engine.
"""

import unittest

from apps.api.domain.transaction import Transaction, TransactionStateError
from apps.api.domain.transaction_engine import transition_transaction
from apps.api.domain.types import Currency, RejectionReason, TransactionState


class TestDomainTransaction(unittest.TestCase):
    """Test Transaction state machine, legal transitions, and forbidden transition enforcement."""

    def setUp(self) -> None:
        self.tx = Transaction(
            buyer_id="buyer-1",
            merchant_id="merchant-1",
            mandate_id="mandate-1",
            mandate_version=1,
            policy_version=1,
            amount_paise=300000,
            currency=Currency.INR,
            state=TransactionState.DRAFT,
        )

    def test_full_legal_transaction_lifecycle(self) -> None:
        # DRAFT -> PROPOSED
        t1 = transition_transaction(self.tx, TransactionState.PROPOSED)
        self.assertEqual(t1.state, TransactionState.PROPOSED)

        # PROPOSED -> VALIDATING
        t2 = transition_transaction(t1, TransactionState.VALIDATING)
        self.assertEqual(t2.state, TransactionState.VALIDATING)

        # VALIDATING -> RESERVED
        t3 = transition_transaction(t2, TransactionState.RESERVED)
        self.assertEqual(t3.state, TransactionState.RESERVED)

        # RESERVED -> AUTHORIZED
        t4 = transition_transaction(
            t3, TransactionState.AUTHORIZED, nonce="nonce-hex-1234567890abcdef"
        )
        self.assertEqual(t4.state, TransactionState.AUTHORIZED)
        self.assertTrue(t4.is_executable())

        # AUTHORIZED -> EXECUTING
        t5 = transition_transaction(t4, TransactionState.EXECUTING)
        self.assertEqual(t5.state, TransactionState.EXECUTING)

        # EXECUTING -> SUCCESS
        t6 = transition_transaction(t5, TransactionState.SUCCESS, razorpay_order_id="order_123")
        self.assertEqual(t6.state, TransactionState.SUCCESS)

        # SUCCESS -> COMMITTED
        t7 = transition_transaction(t6, TransactionState.COMMITTED)
        self.assertEqual(t7.state, TransactionState.COMMITTED)

        # COMMITTED -> COMPLETED
        t8 = transition_transaction(t7, TransactionState.COMPLETED)
        self.assertEqual(t8.state, TransactionState.COMPLETED)

        # COMPLETED -> RECEIPT
        t9 = transition_transaction(t8, TransactionState.RECEIPT)
        self.assertEqual(t9.state, TransactionState.RECEIPT)
        self.assertTrue(t9.is_terminal())

    def test_rejection_transition_and_invariant(self) -> None:
        t1 = transition_transaction(self.tx, TransactionState.PROPOSED)
        t2 = transition_transaction(t1, TransactionState.VALIDATING)

        # Transitioning to REJECTED requires rejection_reason
        with self.assertRaises(ValueError):
            transition_transaction(t2, TransactionState.REJECTED)

        # Valid REJECTED transition
        t_rejected = transition_transaction(
            t2,
            TransactionState.REJECTED,
            rejection_reason=RejectionReason.MANDATE_EXPIRED,
            rejection_detail="Mandate expired 5 mins ago",
        )
        self.assertEqual(t_rejected.state, TransactionState.REJECTED)
        self.assertEqual(t_rejected.rejection_reason, RejectionReason.MANDATE_EXPIRED)
        self.assertTrue(t_rejected.is_terminal())

    def test_section_26_forbidden_transitions(self) -> None:
        # REJECTED -> EXECUTING (forbidden)
        t1 = transition_transaction(self.tx, TransactionState.PROPOSED)
        t2 = transition_transaction(t1, TransactionState.VALIDATING)
        t_rejected = transition_transaction(
            t2,
            TransactionState.REJECTED,
            rejection_reason=RejectionReason.MANDATE_EXPIRED,
        )
        with self.assertRaises(TransactionStateError):
            transition_transaction(t_rejected, TransactionState.EXECUTING)

        # COMPLETED -> EXECUTING (forbidden)
        t_completed = Transaction(
            buyer_id="b-1",
            merchant_id="m-1",
            mandate_id="man-1",
            mandate_version=1,
            policy_version=1,
            state=TransactionState.COMPLETED,
        )
        with self.assertRaises(TransactionStateError):
            transition_transaction(t_completed, TransactionState.EXECUTING)


if __name__ == "__main__":
    unittest.main()
