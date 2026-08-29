"""
Unit tests verifying S05.4.1 Persistence Integration Architecture Mapping.
"""

from __future__ import annotations

import os
import unittest

from db.repository import (
    AuditRepository,
    BaseRepository,
    BudgetRepository,
    MandateRepository,
    MerchantRepository,
    NonceRepository,
    ReceiptRepository,
    ReplayRepository,
    StepUpRepository,
    TransactionRepository,
)


class TestPersistenceIntegrationArchitectureMapping(unittest.TestCase):
    """Test suite verifying architecture mapping contracts and documentation existence."""

    def test_architecture_document_exists(self) -> None:
        """Verify the S05.4.1 architecture specification document exists on disk."""
        doc_path = os.path.join(
            os.path.dirname(__file__),
            "../../docs/architecture/M05_4_1_persistence_integration_architecture.md",
        )
        norm_path = os.path.normpath(doc_path)
        self.assertTrue(
            os.path.isfile(norm_path),
            f"Architecture document missing at {norm_path}",
        )

    def test_repository_suite_availability(self) -> None:
        """Verify all 10 required repositories are exported and subclass BaseRepository."""
        repos = [
            MerchantRepository,
            MandateRepository,
            TransactionRepository,
            BudgetRepository,
            StepUpRepository,
            ReplayRepository,
            NonceRepository,
            AuditRepository,
            ReceiptRepository,
        ]

        for repo_cls in repos:
            self.assertTrue(
                issubclass(repo_cls, BaseRepository),
                f"{repo_cls.__name__} does not inherit from BaseRepository!",
            )

    def test_repositories_prohibit_commit_and_rollback(self) -> None:
        """Verify repositories do not expose commit or rollback methods directly."""
        repos = [
            MerchantRepository,
            MandateRepository,
            TransactionRepository,
            BudgetRepository,
            StepUpRepository,
            ReplayRepository,
            NonceRepository,
            AuditRepository,
            ReceiptRepository,
        ]

        forbidden = ["commit", "rollback", "begin"]

        for repo_cls in repos:
            for method_name in forbidden:
                self.assertFalse(
                    hasattr(repo_cls, method_name),
                    f"{repo_cls.__name__} exposes forbidden transaction ownership method '{method_name}'!",
                )


if __name__ == "__main__":
    unittest.main()
