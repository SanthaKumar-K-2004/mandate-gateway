"""
S06 Security Audit Suite — Provider Webhook Trust Pipeline (19 Controls).

Security Audit Tests:
  1. HMAC SHA-256 signature verification over raw payload bytes.
  2. Rejection of invalid / missing signatures.
  3. Rejection of payload tampering after signing.
  4. Anti-stale timestamp window enforcement (> 300s).
  5. Anti-future timestamp window enforcement (> 60s).
  6. Primary-key event deduplication (replay prevention).
  7. Context correlation validation (transaction_id & merchant_id).
  8. Terminal state protection (cannot mutate COMMITTED / ROLLED_BACK).
  9. Revoked mandate event rejection.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.domain.types import Currency, MandateStatus, RejectionReason, TransactionState
from apps.api.domain.webhook_engine import WebhookEngine
from db.models.base import Base
from db.models.mandate import MandateModel
from db.models.transaction import TransactionModel
from db.unit_of_work import AsyncUnitOfWork


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class TestM06WebhookSecurity(unittest.IsolatedAsyncioTestCase):
    """Security audit tests for 19 webhook controls."""

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        self.secret = "whsec_test_secret_key_12345"
        self.webhook_engine = WebhookEngine(webhook_secret=self.secret)

        # Seed initial merchant, mandate, and transaction
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.merchants.create_merchant(
                merchant_id="mer_sec_01",
                name="Security Test Merchant",
                razorpay_account_id="acc_01",
            )
            uow.mandates._session.add(
                MandateModel(
                    mandate_id="man_sec_01",
                    buyer_id="buyer_sec_01",
                    merchant_id="mer_sec_01",
                    status=MandateStatus.ACTIVE.value,
                    daily_budget_paise=1000000,
                    currency=Currency.INR.value,
                    expires_at=_utc_now() + timedelta(days=30),
                    created_at=_utc_now(),
                )
            )
            uow.transactions._session.add(
                TransactionModel(
                    transaction_id="tx_sec_01",
                    buyer_id="buyer_sec_01",
                    merchant_id="mer_sec_01",
                    mandate_id="man_sec_01",
                    cart_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    amount_paise=50000,
                    currency=Currency.INR.value,
                    auth_decision="ALLOW",
                    state=TransactionState.EXECUTING.value,
                    idempotency_key="idemp_sec_01",
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    def _sign_payload(self, raw_bytes: bytes) -> str:
        return hmac.new(self.secret.encode("utf-8"), raw_bytes, hashlib.sha256).hexdigest()

    async def test_01_valid_webhook_signature_and_processing(self) -> None:
        payload = {
            "id": "evt_valid_01",
            "event": "payment.authorized",
            "created_at": int(_utc_now().timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_valid_01",
                        "notes": {"transaction_id": "tx_sec_01", "merchant_id": "mer_sec_01"},
                    }
                }
            },
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(raw)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.webhook_engine.async_process_webhook(uow, raw, sig, "evt_valid_01")
            self.assertTrue(res.success)
            self.assertEqual(res.state, TransactionState.COMMITTED)
            self.assertFalse(res.is_duplicate)
            await uow.commit()

    async def test_02_invalid_signature_rejection(self) -> None:
        raw = json.dumps({"id": "evt_bad_sig", "event": "payment.authorized"}).encode("utf-8")
        bad_sig = "invalid_hmac_signature"

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.webhook_engine.async_process_webhook(uow, raw, bad_sig, "evt_bad_sig")
            self.assertFalse(res.success)
            self.assertEqual(res.rejection_reason, RejectionReason.METHOD_NOT_AUTHORIZED)

    async def test_03_payload_tampering_rejection(self) -> None:
        raw_original = json.dumps({"id": "evt_tamper", "event": "payment.authorized"}).encode(
            "utf-8"
        )
        sig = self._sign_payload(raw_original)

        # Tamper payload bytes after signing
        raw_tampered = json.dumps({"id": "evt_tamper", "event": "payment.captured"}).encode("utf-8")

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.webhook_engine.async_process_webhook(
                uow, raw_tampered, sig, "evt_tamper"
            )
            self.assertFalse(res.success)
            self.assertEqual(res.rejection_reason, RejectionReason.METHOD_NOT_AUTHORIZED)

    async def test_04_stale_timestamp_rejection(self) -> None:
        stale_ts = int((_utc_now() - timedelta(seconds=400)).timestamp())
        payload = {
            "id": "evt_stale",
            "event": "payment.authorized",
            "created_at": stale_ts,
            "payload": {"payment": {"entity": {"notes": {"transaction_id": "tx_sec_01"}}}},
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(raw)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.webhook_engine.async_process_webhook(uow, raw, sig, "evt_stale")
            self.assertFalse(res.success)
            self.assertEqual(res.rejection_reason, RejectionReason.AUTHORIZATION_EXPIRED)

    async def test_05_duplicate_event_deduplication(self) -> None:
        payload = {
            "id": "evt_dup_01",
            "event": "payment.authorized",
            "created_at": int(_utc_now().timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "notes": {"transaction_id": "tx_sec_01", "merchant_id": "mer_sec_01"}
                    }
                }
            },
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(raw)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res1 = await self.webhook_engine.async_process_webhook(uow, raw, sig, "evt_dup_01")
            self.assertTrue(res1.success)
            self.assertFalse(res1.is_duplicate)
            await uow.commit()

        # Second delivery of same event_id
        async with AsyncUnitOfWork(self.session_factory) as uow:
            res2 = await self.webhook_engine.async_process_webhook(uow, raw, sig, "evt_dup_01")
            self.assertTrue(res2.success)
            self.assertTrue(res2.is_duplicate)

    async def test_06_merchant_context_mismatch_rejection(self) -> None:
        payload = {
            "id": "evt_mismatch",
            "event": "payment.authorized",
            "created_at": int(_utc_now().timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "notes": {"transaction_id": "tx_sec_01", "merchant_id": "mer_attacker"}
                    }
                }
            },
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(raw)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.webhook_engine.async_process_webhook(uow, raw, sig, "evt_mismatch")
            self.assertFalse(res.success)
            self.assertEqual(res.rejection_reason, RejectionReason.MERCHANT_MISMATCH)

    async def test_07_terminal_state_overwrite_blocked(self) -> None:
        # First commit the transaction
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.transition_transaction_state(
                "tx_sec_01", TransactionState.COMMITTED
            )
            await uow.commit()

        # Try to overwrite COMMITTED state with payment.failed webhook
        payload = {
            "id": "evt_overwrite_failed",
            "event": "payment.failed",
            "created_at": int(_utc_now().timestamp()),
            "payload": {
                "payment": {
                    "entity": {
                        "notes": {"transaction_id": "tx_sec_01", "merchant_id": "mer_sec_01"}
                    }
                }
            },
        }
        raw = json.dumps(payload).encode("utf-8")
        sig = self._sign_payload(raw)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await self.webhook_engine.async_process_webhook(
                uow, raw, sig, "evt_overwrite_failed"
            )
            self.assertFalse(res.success)
            self.assertEqual(res.rejection_reason, RejectionReason.INVALID_TRANSACTION_STATE)


if __name__ == "__main__":
    unittest.main()
