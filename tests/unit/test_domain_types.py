"""
Unit tests for domain types & enumerations (S01.1).
"""

import unittest

from apps.api.domain.types import (
    Currency,
    MandateStatus,
    McpOperation,
    PaymentResultState,
    Region,
    RejectionReason,
    TransactionState,
)


class TestDomainTypes(unittest.TestCase):
    """Test completeness, uniqueness, and helper methods of domain enumerations."""

    def test_currency_values(self) -> None:
        self.assertEqual(Currency.INR.value, "INR")
        self.assertEqual(Currency.USD.value, "USD")

    def test_region_values(self) -> None:
        self.assertEqual(Region.IN.value, "IN")

    def test_mandate_status_helpers(self) -> None:
        self.assertTrue(MandateStatus.ACTIVE.can_execute())
        self.assertFalse(MandateStatus.DRAFT.can_execute())
        self.assertFalse(MandateStatus.SUSPENDED.can_execute())
        self.assertFalse(MandateStatus.REVOKED.can_execute())
        self.assertFalse(MandateStatus.EXPIRED.can_execute())

        self.assertTrue(MandateStatus.REVOKED.is_terminal())
        self.assertTrue(MandateStatus.EXPIRED.is_terminal())
        self.assertFalse(MandateStatus.ACTIVE.is_terminal())

    def test_transaction_state_legal_transitions(self) -> None:
        # Check standard flow
        self.assertTrue(TransactionState.DRAFT.can_transition_to(TransactionState.PROPOSED))
        self.assertTrue(TransactionState.PROPOSED.can_transition_to(TransactionState.VALIDATING))
        self.assertTrue(TransactionState.VALIDATING.can_transition_to(TransactionState.RESERVED))
        self.assertTrue(TransactionState.RESERVED.can_transition_to(TransactionState.AUTHORIZED))
        self.assertTrue(TransactionState.AUTHORIZED.can_transition_to(TransactionState.EXECUTING))
        self.assertTrue(TransactionState.EXECUTING.can_transition_to(TransactionState.SUCCESS))
        self.assertTrue(TransactionState.SUCCESS.can_transition_to(TransactionState.COMMITTED))
        self.assertTrue(TransactionState.COMMITTED.can_transition_to(TransactionState.COMPLETED))
        self.assertTrue(TransactionState.COMPLETED.can_transition_to(TransactionState.RECEIPT))

    def test_transaction_state_forbidden_transitions(self) -> None:
        # Section 26 forbidden transitions
        forbidden_pairs = [
            (TransactionState.REJECTED, TransactionState.EXECUTING),
            (TransactionState.EXPIRED, TransactionState.EXECUTING),
            (TransactionState.CONSUMED, TransactionState.EXECUTING),
            (TransactionState.COMPLETED, TransactionState.EXECUTING),
            (TransactionState.ROLLED_BACK, TransactionState.COMMITTED),
        ]
        for src, target in forbidden_pairs:
            self.assertFalse(
                src.can_transition_to(target),
                f"Transition {src.value} -> {target.value} should be forbidden",
            )

    def test_mcp_operations_blocked_by_default(self) -> None:
        self.assertTrue(McpOperation.PAYOUT.is_blocked_by_default)
        self.assertTrue(McpOperation.SETTLEMENT.is_blocked_by_default)
        self.assertTrue(McpOperation.BANK_TRANSFER.is_blocked_by_default)
        self.assertFalse(McpOperation.CREATE_ORDER.is_blocked_by_default)
        self.assertFalse(McpOperation.CREATE_PAYMENT_LINK.is_blocked_by_default)

    def test_payment_result_state_retryable(self) -> None:
        self.assertTrue(PaymentResultState.UNKNOWN.is_retryable())
        self.assertFalse(PaymentResultState.SUCCESS.is_retryable())
        self.assertFalse(PaymentResultState.FAILED.is_retryable())

    def test_rejection_reasons_uniqueness(self) -> None:
        reasons = list(RejectionReason)
        values = [r.value for r in reasons]
        self.assertEqual(len(values), len(set(values)), "RejectionReason values must be unique")


if __name__ == "__main__":
    unittest.main()
