"""
Integration tests for S05.3.7 ReceiptRepository against SQLite in-memory database.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.receipt_signer import ActionReceiptSigner, Ed25519KeyManager
from apps.api.domain.types import AuditEventType, Currency, PolicyDecision
from db.models.base import Base
from db.repository.audit_repository import AuditRepository
from db.repository.merchant_repository import MerchantRepository
from db.repository.receipt_repository import ReceiptRepository
from db.repository.transaction_repository import TransactionRepository


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestReceiptRepositoryIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration test suite for ReceiptRepository using SQLite in-memory engine."""

    async def asyncSetUp(self) -> None:
        """Set up in-memory SQLite database and repository session."""
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.session = self.session_factory()
        self.merchant_repo = MerchantRepository(self.session)
        self.tx_repo = TransactionRepository(self.session)
        self.audit_repo = AuditRepository(self.session)
        self.receipt_repo = ReceiptRepository(self.session)

        # Seed merchant, transaction, and audit event for FK compliance
        await self.merchant_repo.create_merchant("m_rcpt_1", "Receipt Merchant")
        await self.tx_repo.create_transaction(
            transaction_id="tx_rcpt_1",
            buyer_id="buyer_rcpt_1",
            merchant_id="m_rcpt_1",
            mandate_id="man_rcpt_1",
            amount_paise=150000,
            cart_hash="a" * 64,
            idempotency_key="idemp_rcpt_1",
        )
        self.audit_evt = await self.audit_repo.append_event(
            event_type=AuditEventType.PAYMENT_SUCCESS,
            transaction_id="tx_rcpt_1",
            mandate_id="man_rcpt_1",
            merchant_id="m_rcpt_1",
            buyer_id="buyer_rcpt_1",
            payload={"amount": 150000},
        )
        await self.session.commit()

    async def asyncTearDown(self) -> None:
        """Close session and dispose engine."""
        await self.session.close()
        await self.engine.dispose()

    async def test_receipt_persistence_retrieval_and_ed25519_integrity(self) -> None:
        """Verify receipt creation with Ed25519 signature, persistence across session, and verification."""
        key_mgr = Ed25519KeyManager.generate()
        signer = ActionReceiptSigner(key_mgr)

        signed_rcpt = signer.sign_receipt(
            receipt_id="rcpt_integ_1",
            transaction_id="tx_rcpt_1",
            mandate_id="man_rcpt_1",
            merchant_id="m_rcpt_1",
            policy_version=1,
            cart_hash="a" * 64,
            amount_paise=150000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
            audit_hash=self.audit_evt.event_hash,
        )

        pubkey_hex = key_mgr.get_public_key_hex()

        # Persist receipt
        db_rcpt = await self.receipt_repo.create_receipt(
            receipt_id=signed_rcpt.receipt_id,
            transaction_id=signed_rcpt.transaction_id,
            audit_event_id=self.audit_evt.event_id,
            canonical_payload_hash=signed_rcpt.canonical_payload_hash,
            signature_hex=signed_rcpt.signature,  # type: ignore[arg-type]
            public_key_hex=pubkey_hex,
        )
        await self.session.commit()

        self.assertEqual(db_rcpt.receipt_id, "rcpt_integ_1")

        # Verify persistence and retrieval in a fresh session
        async with self.session_factory() as session2:
            repo2 = ReceiptRepository(session2)

            retrieved = await repo2.get_receipt("rcpt_integ_1")
            self.assertIsNotNone(retrieved)
            assert retrieved is not None
            self.assertEqual(retrieved.transaction_id, "tx_rcpt_1")
            self.assertEqual(retrieved.canonical_payload_hash, signed_rcpt.canonical_payload_hash)
            self.assertEqual(retrieved.signature_hex, signed_rcpt.signature)

            # Lookup by transaction
            tx_retrieved = await repo2.get_receipt_for_transaction("tx_rcpt_1")
            self.assertIsNotNone(tx_retrieved)
            self.assertEqual(tx_retrieved.receipt_id, "rcpt_integ_1")  # type: ignore[union-attr]

            # Lookup by audit event
            evt_receipts = await repo2.get_receipt_for_audit_event(self.audit_evt.event_id)
            self.assertEqual(len(evt_receipts), 1)
            self.assertEqual(evt_receipts[0].receipt_id, "rcpt_integ_1")

    async def test_duplicate_receipt_id_rejected(self) -> None:
        """Verify attempting to create a receipt with duplicate receipt_id raises ValueError."""
        await self.receipt_repo.create_receipt(
            receipt_id="rcpt_dup",
            transaction_id="tx_rcpt_1",
            audit_event_id=self.audit_evt.event_id,
            canonical_payload_hash="hash_1",
            signature_hex="sig_1",
            public_key_hex="pub_1",
        )
        await self.session.commit()

        async with self.session_factory() as session2:
            repo2 = ReceiptRepository(session2)
            with self.assertRaises(ValueError) as ctx:
                await repo2.create_receipt(
                    receipt_id="rcpt_dup",
                    transaction_id="tx_rcpt_1",
                    audit_event_id=self.audit_evt.event_id,
                    canonical_payload_hash="hash_2",
                    signature_hex="sig_2",
                    public_key_hex="pub_2",
                )

            self.assertIn("integrity constraint", str(ctx.exception))

    async def test_transaction_rollback_leaves_no_partial_receipt(self) -> None:
        """Verify rolling back session removes uncommitted receipt."""
        await self.receipt_repo.create_receipt(
            receipt_id="rcpt_rollback",
            transaction_id="tx_rcpt_1",
            audit_event_id=self.audit_evt.event_id,
            canonical_payload_hash="hash_rb",
            signature_hex="sig_rb",
            public_key_hex="pub_rb",
        )
        await self.session.rollback()

        retrieved = await self.receipt_repo.get_receipt("rcpt_rollback")
        self.assertIsNone(retrieved)


if __name__ == "__main__":
    unittest.main()
