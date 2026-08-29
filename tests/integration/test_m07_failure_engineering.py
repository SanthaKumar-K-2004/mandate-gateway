"""
M07 — Deep Production Resilience, Failure Engineering & System Integrity
Integration Test Suite.

Failure domains covered:
  F-01  UoW explicit-commit policy: uncommitted exit rolls back completely.
  F-02  UoW exception-path rollback: exception inside UoW rolls back without data corruption.
  F-03  UoW closed-state guard: operations on a closed UoW fail immediately.
  F-04  Nested UoW prohibition: re-entering active UoW raises NestedUnitOfWorkForbiddenError.
  F-05  Double-commit guard: committing a UoW twice raises UnitOfWorkError.
  F-06  Illegal transition: EXECUTING -> AUTHORIZED rejected deterministically.
  F-07  Terminal-state guard: REJECTED -> EXECUTING rejected; terminal state is immutable.
  F-08  UNKNOWN provider outcome: transaction stays EXECUTING.
  F-09  Idempotency key context conflict: mismatched context raises ValueError.
  F-10  Idempotency key same-context: returns existing transaction record.
  F-11  REJECT authorization decision fails closed.
  F-12  Missing BUDGET_RESERVATION control fails closed.
  F-13  Amount mismatch fails closed.
  F-14  Cart hash tamper fails closed.
  F-15  Non-AUTHORIZED state fails execution gate.
  F-16  Committed result idempotent replay.
  F-17  UNKNOWN outcome triggers reconciliation on re-execution.
  F-18  Nonce single-use guarantee.
  F-19  Nonce context binding: wrong transaction_id rejected.
  F-20  Nonce TTL expiry.
  F-21  Replay fingerprint deduplication.
  F-22  Replay fingerprint context conflict.
  F-23  Budget overshoot rejected.
  F-24  Releasing committed reservation raises ValueError.
  F-25  Released reservation restores full available budget.
  F-26  Audit chain integrity after sequential appends.
  F-27  Tampered audit hash detected by verify_chain().
  F-28  REVOKED mandate cannot be reactivated (terminal state).
"""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult, SecurityControlOutcome
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.contracts.merchant import McpOperation
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    Currency,
    MandateStatus,
    PaymentResultState,
    PolicyDecision,
    RejectionReason,
    TransactionState,
)
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork, NestedUnitOfWorkForbiddenError, UnitOfWorkError


def _uid(prefix: str = "id") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_auth_result(
    decision: PolicyDecision = PolicyDecision.ALLOW,
    extra_controls: list[SecurityControlOutcome] | None = None,
) -> AuthorizationResult:
    """Build a minimal AuthorizationResult with all required controls."""
    required = [
        SecurityControlOutcome("MANDATE_EVALUATION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("MERCHANT_POLICY", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("CART_INTEGRITY", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("BUDGET_RESERVATION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("REPLAY_PROTECTION", True, PolicyDecision.ALLOW),
        SecurityControlOutcome("NONCE_VALIDATION", True, PolicyDecision.ALLOW),
    ]
    controls = required + (extra_controls or [])
    return AuthorizationResult(
        decision=decision,
        control_outcomes=controls,
        decision_trace={"authorization_reference": f"auth_{uuid.uuid4().hex[:8]}"},
        rejection_reason=(
            RejectionReason.METHOD_NOT_AUTHORIZED if decision != PolicyDecision.ALLOW else None
        ),
    )


def _make_transaction(
    tx_id: str,
    merchant_id: str,
    buyer_id: str,
    mandate_id: str,
    amount_paise: int = 5000,
    cart_hash: str | None = None,
    state: TransactionState = TransactionState.AUTHORIZED,
) -> Transaction:
    return Transaction(
        transaction_id=tx_id,
        buyer_id=buyer_id,
        merchant_id=merchant_id,
        mandate_id=mandate_id,
        mandate_version=1,
        policy_version=1,
        amount_paise=amount_paise,
        cart_hash=cart_hash or "a" * 64,
        state=state,
    )


def _make_proposal(
    tx_id: str,
    merchant_id: str,
    buyer_id: str,
    mandate_id: str,
    amount_paise: int = 5000,
    cart_hash: str | None = None,
    operation: McpOperation = McpOperation.CREATE_ORDER,
    idempotency_key: str | None = None,
) -> PaymentExecuteProposalRequest:
    return PaymentExecuteProposalRequest(
        transaction_id=tx_id,
        merchant_id=merchant_id,
        buyer_id=buyer_id,
        mandate_id=mandate_id,
        amount_paise=amount_paise,
        currency=Currency.INR,
        cart_hash=cart_hash or "a" * 64,
        operation=operation,
        idempotency_key=idempotency_key or f"idem_{tx_id}",
    )


class TestM07UoWBoundaryFailures(unittest.IsolatedAsyncioTestCase):
    """F-01 through F-05: Unit of Work transaction boundary and lifecycle failures."""

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

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def _create_merchant(self, uow, m_id):
        await uow.merchants.create_merchant(m_id, f"Store {m_id}", f"acc_{m_id[:6]}")
        await uow.merchants.create_policy(
            policy_id=f"pol_{m_id[:6]}",
            merchant_id=m_id,
            policy_version="1",
            autonomous_limit_paise=500_000,
            step_up_threshold_paise=400_000,
            allowed_operations=["CREATE_ORDER", "CREATE_PAYMENT_LINK", "FETCH_PAYMENT"],
        )

    async def test_F01_uncommitted_exit_rolls_back(self) -> None:
        """UoW that exits without explicit commit must not persist changes."""
        m_id = _uid("mer")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await self._create_merchant(uow, m_id)
            # No commit — fail-closed rollback
        async with AsyncUnitOfWork(self.session_factory) as uow:
            merchant = await uow.merchants.get_by_id(m_id)
            self.assertIsNone(merchant, "Uncommitted merchant must not be durable.")

    async def test_F02_exception_path_rolls_back(self) -> None:
        """Exception inside UoW block must roll back all mutations atomically."""
        m_id = _uid("mer")
        with self.assertRaises(RuntimeError):
            async with AsyncUnitOfWork(self.session_factory) as uow:
                await self._create_merchant(uow, m_id)
                raise RuntimeError("Simulated crash before commit")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            merchant = await uow.merchants.get_by_id(m_id)
            self.assertIsNone(merchant, "Exception-path merchant must not be durable.")

    async def test_F03_closed_uow_rejects_operations(self) -> None:
        """Accessing a closed UoW must raise UnitOfWorkClosedError."""
        from db.unit_of_work import UnitOfWorkClosedError

        uow = AsyncUnitOfWork(self.session_factory)
        async with uow:
            pass
        with self.assertRaises(UnitOfWorkClosedError):
            _ = uow.merchants

    async def test_F04_nested_uow_is_forbidden(self) -> None:
        """Re-entering an already-active UoW must raise NestedUnitOfWorkForbiddenError."""
        uow = AsyncUnitOfWork(self.session_factory)
        async with uow:
            with self.assertRaises(NestedUnitOfWorkForbiddenError):
                async with uow:
                    pass

    async def test_F05_double_commit_raises_error(self) -> None:
        """Committing a UoW twice must raise UnitOfWorkError."""
        m_id = _uid("mer")
        uow = AsyncUnitOfWork(self.session_factory)
        async with uow:
            await self._create_merchant(uow, m_id)
            await uow.commit()
            with self.assertRaises(UnitOfWorkError):
                await uow.commit()


class TestM07TransactionStateMachineFailures(unittest.IsolatedAsyncioTestCase):
    """F-06 through F-10: Transaction state machine boundary failures."""

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
            await uow.merchants.create_merchant(self.m_id, "Failure Store", f"acc_{self.m_id[:6]}")
            await uow.merchants.create_policy(
                policy_id=f"pol_{self.m_id[:6]}",
                merchant_id=self.m_id,
                policy_version="1",
                autonomous_limit_paise=500_000,
                step_up_threshold_paise=400_000,
                allowed_operations=["CREATE_ORDER", "CREATE_PAYMENT_LINK", "FETCH_PAYMENT"],
            )
            await uow.mandates.create_mandate(
                mandate_id=self.man_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                daily_budget_paise=100_000,
                status=MandateStatus.ACTIVE.value,
                expires_at=now + timedelta(days=30),
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def _create_tx_in_db(self, tx_id, state="AUTHORIZED"):
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,
                cart_hash="a" * 64,
                idempotency_key=f"idem_{tx_id}",
                state=state,
            )
            await uow.commit()

    async def test_F06_illegal_transition_executing_to_authorized(self) -> None:
        """EXECUTING -> AUTHORIZED is not a legal transition; must raise ValueError."""
        tx_id = _uid("tx")
        await self._create_tx_in_db(tx_id, state="EXECUTING")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.transactions.transition_transaction_state(
                    tx_id, TransactionState.AUTHORIZED
                )

    async def test_F07_terminal_state_is_immutable(self) -> None:
        """Transitioning from a terminal state (REJECTED) must raise ValueError."""
        tx_id = _uid("tx")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,
                cart_hash="a" * 64,
                idempotency_key=f"idem_term_{tx_id}",
                state="REJECTED",
            )
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.transactions.transition_transaction_state(
                    tx_id, TransactionState.EXECUTING
                )

    async def test_F08_unknown_provider_outcome_stays_executing(self) -> None:
        """UNKNOWN provider status must not automatically advance transaction state."""
        tx_id = _uid("tx")
        await self._create_tx_in_db(tx_id, state="AUTHORIZED")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.mark_provider_dispatch_started(tx_id)
            await uow.transactions.record_provider_outcome(tx_id, "UNKNOWN")
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            tx = await uow.transactions.get_transaction(tx_id)
            self.assertIsNotNone(tx)
            assert tx is not None
            self.assertEqual(
                tx.state,
                TransactionState.EXECUTING.value,
                "UNKNOWN outcome must not auto-advance transaction from EXECUTING.",
            )
            self.assertEqual(tx.provider_status, "UNKNOWN")

    async def test_F09_idempotency_key_context_conflict(self) -> None:
        """Reusing an idempotency key with different context must raise ValueError."""
        tx_id_1 = _uid("tx")
        idem_key = f"shared_key_{uuid.uuid4().hex[:8]}"
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id_1,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,
                cart_hash="a" * 64,
                idempotency_key=idem_key,
            )
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.transactions.create_transaction(
                    transaction_id=_uid("tx"),
                    buyer_id=self.b_id,
                    merchant_id=self.m_id,
                    mandate_id=self.man_id,
                    amount_paise=99999,  # DIFFERENT — context conflict
                    cart_hash="a" * 64,
                    idempotency_key=idem_key,
                )

    async def test_F10_idempotency_key_same_context_returns_existing(self) -> None:
        """Reusing idempotency key with matching context must return existing transaction."""
        tx_id = _uid("tx")
        idem_key = f"same_ctx_{uuid.uuid4().hex[:8]}"
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,
                cart_hash="a" * 64,
                idempotency_key=idem_key,
            )
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            replay = await uow.transactions.create_transaction(
                transaction_id=_uid("tx"),  # Different new ID
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=5000,  # Same context
                cart_hash="a" * 64,
                idempotency_key=idem_key,
            )
            self.assertEqual(
                replay.transaction_id,
                tx_id,
                "Matching idempotency context must return existing transaction.",
            )


class TestM07ExecutionEngineFailures(unittest.IsolatedAsyncioTestCase):
    """F-11 through F-17: PaymentExecutionService pre-execution gate failures."""

    def setUp(self) -> None:
        self.adapter = MockRazorpayAdapter()
        self.service = PaymentExecutionService(self.adapter)
        self.m_id = _uid("mer")
        self.man_id = _uid("man")
        self.b_id = _uid("buy")
        self.tx_id = _uid("tx")
        self.cart_hash = "b" * 64

    def _make_tx(self, **kwargs: Any) -> Transaction:
        kwargs.setdefault("cart_hash", self.cart_hash)
        return _make_transaction(self.tx_id, self.m_id, self.b_id, self.man_id, **kwargs)

    def _make_prop(self, **kwargs: Any) -> PaymentExecuteProposalRequest:
        kwargs.setdefault("cart_hash", self.cart_hash)
        return _make_proposal(self.tx_id, self.m_id, self.b_id, self.man_id, **kwargs)

    def test_F11_rejected_authorization_fails_closed(self) -> None:
        """Execution with REJECT authorization must fail closed without provider call."""
        tx = self._make_tx()
        proposal = self._make_prop()
        auth = _make_auth_result(decision=PolicyDecision.REJECT)
        result = self.service.execute_payment(proposal, auth, tx)
        self.assertFalse(result.success)
        self.assertEqual(result.state, TransactionState.REJECTED)

    def test_F12_missing_budget_control_fails_closed(self) -> None:
        """Missing BUDGET_RESERVATION control must reject execution fail-closed."""
        controls = [
            SecurityControlOutcome("MANDATE_EVALUATION", True, PolicyDecision.ALLOW),
            SecurityControlOutcome("MERCHANT_POLICY", True, PolicyDecision.ALLOW),
            SecurityControlOutcome("CART_INTEGRITY", True, PolicyDecision.ALLOW),
            # BUDGET_RESERVATION intentionally omitted
            SecurityControlOutcome("REPLAY_PROTECTION", True, PolicyDecision.ALLOW),
            SecurityControlOutcome("NONCE_VALIDATION", True, PolicyDecision.ALLOW),
        ]
        auth = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=controls,
            decision_trace={},
        )
        tx = self._make_tx()
        proposal = self._make_prop()
        result = self.service.execute_payment(proposal, auth, tx)
        self.assertFalse(result.success)
        self.assertEqual(result.state, TransactionState.REJECTED)
        self.assertIn("BUDGET_RESERVATION", result.safe_message)

    def test_F13_amount_mismatch_fails_closed(self) -> None:
        """Amount mismatch between proposal and transaction must fail closed."""
        tx = self._make_tx(amount_paise=5000)
        proposal = _make_proposal(
            self.tx_id,
            self.m_id,
            self.b_id,
            self.man_id,
            amount_paise=9999,
            cart_hash=self.cart_hash,
        )
        auth = _make_auth_result()
        result = self.service.execute_payment(proposal, auth, tx)
        self.assertFalse(result.success)
        self.assertEqual(result.state, TransactionState.REJECTED)
        self.assertIn("Amount mismatch", result.safe_message)

    def test_F14_cart_hash_tamper_fails_closed(self) -> None:
        """Tampered cart hash in proposal must be rejected pre-execution."""
        tx = self._make_tx(cart_hash="c" * 64)
        proposal = _make_proposal(
            self.tx_id,
            self.m_id,
            self.b_id,
            self.man_id,
            cart_hash="d" * 64,
        )
        auth = _make_auth_result()
        result = self.service.execute_payment(proposal, auth, tx)
        self.assertFalse(result.success)
        self.assertEqual(result.state, TransactionState.REJECTED)
        self.assertIn("Cart hash mismatch", result.safe_message)

    def test_F15_non_authorized_state_fails_closed(self) -> None:
        """Transaction in RESERVED state (not AUTHORIZED) must fail execution gate."""
        tx = self._make_tx(state=TransactionState.RESERVED)
        proposal = self._make_prop()
        auth = _make_auth_result()
        result = self.service.execute_payment(proposal, auth, tx)
        self.assertFalse(result.success)
        self.assertEqual(result.state, TransactionState.REJECTED)

    def test_F16_committed_result_idempotent_replay(self) -> None:
        """Replaying an execution for a committed transaction returns cached result."""
        # MockRazorpayAdapter succeeds by default — no special configuration needed.
        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter)
        tx = self._make_tx()
        proposal = self._make_prop()
        auth = _make_auth_result()
        result_1 = service.execute_payment(proposal, auth, tx)
        self.assertTrue(result_1.success, "First execution must succeed.")
        result_2 = service.execute_payment(proposal, auth, tx)
        self.assertTrue(result_2.idempotent_replay, "Second execution must be idempotent replay.")
        self.assertEqual(result_1.transaction_id, result_2.transaction_id)
        self.assertEqual(result_1.state, result_2.state)

    def test_F17_unknown_outcome_triggers_reconciliation(self) -> None:
        """Re-execution of an UNKNOWN outcome must trigger reconciliation path."""
        # Phase 1: force UNKNOWN outcome via simulated gateway timeout.
        adapter = MockRazorpayAdapter()
        adapter.set_simulate_timeout(True)
        service = PaymentExecutionService(adapter)
        tx = self._make_tx()
        proposal = self._make_prop()
        auth = _make_auth_result()
        result_1 = service.execute_payment(proposal, auth, tx)
        self.assertEqual(
            result_1.provider_status,
            PaymentResultState.UNKNOWN,
            "Timeout must yield UNKNOWN provider status.",
        )
        self.assertEqual(
            result_1.state,
            TransactionState.EXECUTING,
            "UNKNOWN outcome must leave transaction in EXECUTING state.",
        )
        # Phase 2: reset timeout; reconciliation will call fetch_payment_status → SUCCESS.
        adapter.set_simulate_timeout(False)
        adapter.set_reconciliation_status(PaymentResultState.SUCCESS)
        result_2 = service.execute_payment(proposal, auth, tx)
        self.assertNotEqual(
            result_2.state,
            TransactionState.EXECUTING,
            "Post-reconciliation state must not remain EXECUTING.",
        )
        self.assertTrue(
            result_2.success,
            "Reconciliation with SUCCESS provider status must yield successful result.",
        )


class TestM07NonceFailures(unittest.IsolatedAsyncioTestCase):
    """F-18 through F-20: Nonce single-use and context-binding failure scenarios."""

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

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_F18_nonce_single_use_guarantee(self) -> None:
        """Consuming the same nonce a second time must raise ValueError."""
        nonce_val = f"nonce_{uuid.uuid4().hex}"
        tx_id = _uid("tx")
        man_id = _uid("man")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.nonces.create_nonce(nonce_val, tx_id, man_id)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            rec = await uow.nonces.consume_nonce(nonce_val, tx_id, man_id, ttl_seconds=0)
            self.assertIsNotNone(rec)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.nonces.consume_nonce(nonce_val, tx_id, man_id, ttl_seconds=0)

    async def test_F19_nonce_context_binding_wrong_transaction(self) -> None:
        """Nonce bound to transaction A must be rejected when consumed for transaction B."""
        nonce_val = f"nonce_{uuid.uuid4().hex}"
        tx_id_correct = _uid("tx")
        tx_id_wrong = _uid("tx")
        man_id = _uid("man")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.nonces.create_nonce(nonce_val, tx_id_correct, man_id)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.nonces.consume_nonce(nonce_val, tx_id_wrong, man_id, ttl_seconds=0)

    async def test_F20_nonce_ttl_expiry(self) -> None:
        """Consuming an expired nonce must raise ValueError."""
        nonce_val = f"nonce_{uuid.uuid4().hex}"
        tx_id = _uid("tx")
        man_id = _uid("man")
        past = _utc_now() - timedelta(seconds=400)
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.nonces.create_nonce(nonce_val, tx_id, man_id, created_at=past)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.nonces.consume_nonce(nonce_val, tx_id, man_id, ttl_seconds=300)


class TestM07ReplayFailures(unittest.IsolatedAsyncioTestCase):
    """F-21 through F-22: Replay protection fingerprint failure scenarios."""

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

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_F21_replay_fingerprint_deduplication(self) -> None:
        """Same replay fingerprint within TTL window must be detected as a replay."""
        fp = f"fp_{uuid.uuid4().hex}"
        tx_id = _uid("tx")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            is_replayed, _ = await uow.replay.check_and_record_replay(fp, tx_id)
            self.assertFalse(is_replayed, "First recording must not be a replay.")
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            is_replayed, _ = await uow.replay.check_and_record_replay(fp, tx_id, ttl_seconds=86400)
            self.assertTrue(is_replayed, "Second check within TTL must be detected as replay.")

    async def test_F22_replay_fingerprint_context_conflict(self) -> None:
        """Same fingerprint reused with different transaction_id must raise ValueError."""
        fp = f"fp_{uuid.uuid4().hex}"
        tx_id_1 = _uid("tx")
        tx_id_2 = _uid("tx")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.replay.record_replay_fingerprint(fp, tx_id_1)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.replay.check_and_record_replay(fp, tx_id_2)


class TestM07BudgetFailures(unittest.IsolatedAsyncioTestCase):
    """F-23 through F-25: Budget reservation atomic failure scenarios."""

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
            await uow.merchants.create_merchant(self.m_id, "Budget Store", f"acc_{self.m_id[:6]}")
            await uow.merchants.create_policy(
                policy_id=f"pol_{self.m_id[:6]}",
                merchant_id=self.m_id,
                policy_version="1",
                autonomous_limit_paise=500_000,
                step_up_threshold_paise=400_000,
                allowed_operations=["CREATE_ORDER"],
            )
            await uow.mandates.create_mandate(
                mandate_id=self.man_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                daily_budget_paise=10_000,
                status=MandateStatus.ACTIVE.value,
                expires_at=now + timedelta(days=30),
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_F23_budget_overshoot_rejected(self) -> None:
        """Reservation that would exceed daily_budget_paise must raise ValueError."""
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.budgets.reserve_budget_atomically(
                    reservation_id=_uid("res"),
                    mandate_id=self.man_id,
                    transaction_id=_uid("tx"),
                    requested_paise=20_000,
                )

    async def test_F24_releasing_committed_reservation_fails(self) -> None:
        """Releasing a reservation in COMMITTED state must raise ValueError."""
        res_id = _uid("res")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.budgets.reserve_budget_atomically(
                reservation_id=res_id,
                mandate_id=self.man_id,
                transaction_id=_uid("tx"),
                requested_paise=3_000,
            )
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.budgets.commit_reservation(res_id)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.budgets.release_reservation(res_id)

    async def test_F25_released_reservation_restores_budget(self) -> None:
        """After releasing a reservation, full budget is available again."""
        res_id = _uid("res")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.budgets.reserve_budget_atomically(
                reservation_id=res_id,
                mandate_id=self.man_id,
                transaction_id=_uid("tx"),
                requested_paise=10_000,
            )
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await uow.budgets.reserve_budget_atomically(
                    reservation_id=_uid("res"),
                    mandate_id=self.man_id,
                    transaction_id=_uid("tx"),
                    requested_paise=1,
                )
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.budgets.release_reservation(res_id)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            new_res = await uow.budgets.reserve_budget_atomically(
                reservation_id=_uid("res"),
                mandate_id=self.man_id,
                transaction_id=_uid("tx"),
                requested_paise=10_000,
            )
            self.assertIsNotNone(new_res, "Budget must be fully available after release.")
            await uow.commit()


class TestM07AuditChainFailures(unittest.IsolatedAsyncioTestCase):
    """F-26 through F-27: Audit hash chain integrity and tamper detection."""

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

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_F26_audit_chain_integrity_after_appends(self) -> None:
        """Sequential audit event appends must form a valid, contiguous hash chain."""
        from apps.api.domain.types import AuditEventType

        tx_id = _uid("tx")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.audit.append_event(
                AuditEventType.EXECUTION_AUTHORIZED, transaction_id=tx_id, payload={"step": 1}
            )
            await uow.audit.append_event(
                AuditEventType.PAYMENT_STARTED, transaction_id=tx_id, payload={"step": 2}
            )
            await uow.audit.append_event(
                AuditEventType.PAYMENT_SUCCESS, transaction_id=tx_id, payload={"step": 3}
            )
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            valid, error_msg = await uow.audit.verify_chain()
            self.assertTrue(valid, f"Audit chain must be valid. Error: {error_msg}")
            self.assertIsNone(error_msg)

    async def test_F27_tampered_audit_hash_detected(self) -> None:
        """Mutating an event_hash directly must be detected by verify_chain()."""
        from apps.api.domain.types import AuditEventType
        from db.models.audit import AuditEventModel
        from sqlalchemy import update

        tx_id = _uid("tx")
        async with AsyncUnitOfWork(self.session_factory) as uow:
            evt = await uow.audit.append_event(
                AuditEventType.EXECUTION_AUTHORIZED, transaction_id=tx_id
            )
            await uow.commit()

        async with self.engine.begin() as conn:
            await conn.execute(
                update(AuditEventModel)
                .where(AuditEventModel.event_id == evt.event_id)
                .values(event_hash="0" * 64)
            )

        async with AsyncUnitOfWork(self.session_factory) as uow:
            valid, error_msg = await uow.audit.verify_chain()
            self.assertFalse(valid, "Tampered audit hash must be detected as invalid.")
            self.assertIsNotNone(error_msg)


class TestM07MandateStateFailures(unittest.IsolatedAsyncioTestCase):
    """F-28: Mandate terminal state immutability."""

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

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_F28_revoked_mandate_cannot_be_activated(self) -> None:
        """Transitioning a REVOKED mandate to ACTIVE must raise ValueError."""
        m_id = _uid("mer")
        man_id = _uid("man")
        b_id = _uid("buy")
        now = _utc_now()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.merchants.create_merchant(m_id, "Revoke Store", f"acc_{m_id[:6]}")
            await uow.merchants.create_policy(
                policy_id=f"pol_{m_id[:6]}",
                merchant_id=m_id,
                policy_version="1",
                autonomous_limit_paise=500_000,
                step_up_threshold_paise=400_000,
                allowed_operations=["CREATE_ORDER"],
            )
            await uow.mandates.create_mandate(
                mandate_id=man_id,
                buyer_id=b_id,
                merchant_id=m_id,
                daily_budget_paise=10_000,
                status=MandateStatus.ACTIVE.value,
                expires_at=now + timedelta(days=30),
            )
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.mandates.transition_mandate_status(man_id, MandateStatus.REVOKED.value)
            await uow.commit()
        async with AsyncUnitOfWork(self.session_factory) as uow:
            with self.assertRaises((ValueError, Exception)):
                await uow.mandates.transition_mandate_status(man_id, MandateStatus.ACTIVE.value)


if __name__ == "__main__":
    unittest.main()
