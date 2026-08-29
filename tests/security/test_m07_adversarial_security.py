"""
M07 — Adversarial Security & Reliability Hardening Test Suite.

Dedicated security tests covering context substitution, payload tampering,
webhooks forgery, out-of-order state transitions, audit tampering, and controlled
mutation verification.
"""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult, SecurityControlOutcome
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.contracts.merchant import McpOperation
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    AuditEventType,
    Currency,
    MandateStatus,
    PaymentResultState,
    PolicyDecision,
    TransactionState,
)
from db.models.audit import AuditEventModel
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_auth_result() -> AuthorizationResult:
    controls = [
        SecurityControlOutcome("MANDATE_EVALUATION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("MERCHANT_POLICY", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("CART_INTEGRITY", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("BUDGET_RESERVATION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("REPLAY_PROTECTION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("NONCE_VALIDATION", True, PolicyDecision.ALLOW),
    ]
    return AuthorizationResult(
        decision=PolicyDecision.ALLOW,
        control_outcomes=controls,
        decision_trace={"authorization_reference": f"auth_{uuid.uuid4().hex[:8]}"},
    )


class TestM07AdversarialSecurity(unittest.IsolatedAsyncioTestCase):
    """Adversarial security and system integrity test suite for M07."""

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
        self.m_id = _uid("mer")
        self.man_id = _uid("man")
        self.b_id = _uid("buy")
        now = _utc_now()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.merchants.create_merchant(self.m_id, "Sec Store", f"acc_{self.m_id[:6]}")
            await uow.merchants.create_policy(
                policy_id=f"pol_{self.m_id[:6]}",
                merchant_id=self.m_id,
                policy_version="1",
                autonomous_limit_paise=5_000_000,
                step_up_threshold_paise=4_000_000,
                allowed_operations=["CREATE_ORDER"],
            )
            await uow.mandates.create_mandate(
                mandate_id=self.man_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                daily_budget_paise=5_000_000,
                status=MandateStatus.ACTIVE.value,
                expires_at=now + timedelta(days=30),
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_S01_idempotency_key_context_substitution_rejected(self) -> None:
        """Reusing an execution attempt idempotency key with a different transaction ID fails closed."""
        key = f"idem_sec_{uuid.uuid4().hex[:8]}"
        fp = "a" * 64
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.execution_attempts.claim_attempt(
                transaction_id="tx_original",
                merchant_id=self.m_id,
                idempotency_key=key,
                payload_fingerprint=fp,
            )
            await uow.commit()

        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.execution_attempts.claim_attempt(
                    transaction_id="tx_attacker",
                    merchant_id=self.m_id,
                    idempotency_key=key,
                    payload_fingerprint=fp,
                )

    async def test_S02_payload_fingerprint_tamper_rejected(self) -> None:
        """Reusing an idempotency key with tampered payload fingerprint fails closed."""
        key = f"idem_tamper_{uuid.uuid4().hex[:8]}"
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.execution_attempts.claim_attempt(
                transaction_id="tx_1",
                merchant_id=self.m_id,
                idempotency_key=key,
                payload_fingerprint="original_hash" + "0" * 51,
            )
            await uow.commit()

        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.execution_attempts.claim_attempt(
                    transaction_id="tx_1",
                    merchant_id=self.m_id,
                    idempotency_key=key,
                    payload_fingerprint="tampered_hash" + "0" * 51,
                )

    def test_S03_webhook_signature_forgery_rejected(self) -> None:
        """Webhook payload with invalid HMAC SHA-256 signature is rejected."""
        from apps.api.domain.webhook_engine import WebhookEngine

        engine = WebhookEngine(webhook_secret="super_secret_webhook_key")
        payload_bytes = b'{"event":"payment.captured","payload":{}}'
        invalid_sig = "bad_signature_digest_string"
        valid = engine.verify_signature(payload_bytes, invalid_sig)
        self.assertFalse(valid, "Forged webhook signature must be rejected.")

    async def test_S04_out_of_order_webhook_transition_blocked(self) -> None:
        """A webhook attempting to transition a COMMITTED transaction back to EXECUTING is rejected."""
        tx_id = _uid("tx")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,
                cart_hash="e" * 64,
                idempotency_key=f"idem_{tx_id}",
                state=TransactionState.COMMITTED,
            )
            await uow.commit()

        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(Exception):
                await uow.transactions.transition_transaction_state(
                    tx_id, TransactionState.EXECUTING
                )

    async def test_S05_audit_chain_tamper_detection(self) -> None:
        """Mutating an audit log entry in persistence breaks verify_chain()."""
        tx_id = _uid("tx")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.audit.append_event(AuditEventType.EXECUTION_AUTHORIZED, transaction_id=tx_id)
            await uow.commit()

        # Mutate hash in persistence directly
        async with self.engine.begin() as conn:
            await conn.execute(
                update(AuditEventModel)
                .where(AuditEventModel.transaction_id == tx_id)
                .values(event_hash="corrupted_hash" + "0" * 50)
            )

        async with AsyncUnitOfWork(self.session_factory) as uow:
            valid, error = await uow.audit.verify_chain()
            self.assertFalse(valid, "Tampered audit entry must fail verify_chain().")
            self.assertIsNotNone(error)

    async def test_S06_ambiguous_provider_outcome_remains_executing(self) -> None:
        """Simulated provider gateway timeout preserves EXECUTING state and fails closed."""
        adapter = MockRazorpayAdapter()
        adapter.set_simulate_timeout(True)
        service = PaymentExecutionService(adapter)
        tx_id = _uid("tx")
        cart_hash = "f" * 64
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,
                cart_hash=cart_hash,
                idempotency_key=f"idem_{tx_id}",
                state=TransactionState.AUTHORIZED,
            )
            await uow.commit()

        auth = _make_auth_result()
        tx = Transaction(
            transaction_id=tx_id,
            buyer_id=self.b_id,
            merchant_id=self.m_id,
            mandate_id=self.man_id,
            mandate_version=1,
            policy_version=1,
            amount_paise=5000,
            cart_hash=cart_hash,
            state=TransactionState.AUTHORIZED,
        )
        proposal = PaymentExecuteProposalRequest(
            transaction_id=tx_id,
            merchant_id=self.m_id,
            buyer_id=self.b_id,
            mandate_id=self.man_id,
            amount_paise=5000,
            currency=Currency.INR,
            cart_hash=cart_hash,
            operation=McpOperation.CREATE_ORDER,
            idempotency_key=f"idem_timeout_{tx_id}",
        )

        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await service.async_execute_payment(uow, proposal, auth, tx)
            await uow.commit()

        self.assertFalse(res.success)
        self.assertEqual(res.provider_status, PaymentResultState.UNKNOWN)
        self.assertEqual(res.state, TransactionState.EXECUTING)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            db_tx = await uow.transactions.get_transaction(tx_id)
            self.assertIsNotNone(db_tx)
            assert db_tx is not None
            self.assertEqual(db_tx.state, TransactionState.EXECUTING.value)
            self.assertEqual(db_tx.provider_status, "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
