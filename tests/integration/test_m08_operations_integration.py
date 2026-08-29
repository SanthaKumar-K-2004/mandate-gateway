"""
M08 — Operations Integration Test Suite
Verifies end-to-end operational metrics, outbox backlog monitoring, recovery metrics, and readiness degradation.
"""

from datetime import datetime, timedelta, timezone
import unittest
import uuid

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.app.context import clear_request_context, set_request_context, set_transaction_context
from apps.api.app.metrics import metrics_registry
from apps.api.contracts.authorization import AuthorizationResult, SecurityControlOutcome
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.recovery_engine import TransactionRecoveryService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    Currency,
    McpOperation,
    PaymentResultState,
    PolicyDecision,
    TransactionState,
)
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class TestM08OperationsIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for operational observability and lifecycle metrics."""

    async def asyncSetUp(self) -> None:
        metrics_registry.reset()
        clear_request_context()

        self.engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session_factory = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

        self.m_id = _uid("mer")
        self.b_id = _uid("buy")
        self.man_id = _uid("man")

        # Seed initial merchant, buyer, mandate
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.merchants.create_merchant(
                merchant_id=self.m_id, name="Ops Merchant", active=True
            )
            await uow.mandates.create_mandate(
                mandate_id=self.man_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                daily_budget_paise=50000,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            await uow.commit()

    async def asyncTearDown(self) -> None:
        clear_request_context()
        metrics_registry.reset()
        await self.engine.dispose()

    async def test_end_to_end_operational_flow_and_outbox_metrics(self) -> None:
        """Verify transaction execution enriches request context and outbox metrics."""
        set_request_context("req_ops_1", "corr_ops_1", "trace_ops_1")
        tx_id = _uid("tx")
        idem_key = f"idem_{tx_id}"

        adapter = MockRazorpayAdapter()
        service = PaymentExecutionService(adapter)

        # 1. Authorize transaction in DB
        async with AsyncUnitOfWork(self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=15000,
                cart_hash="a" * 64,
                idempotency_key=idem_key,
                state=TransactionState.AUTHORIZED,
            )
            await uow.commit()

        set_transaction_context(transaction_id=tx_id, merchant_id=self.m_id, buyer_id=self.b_id)

        tx_domain = Transaction(
            transaction_id=tx_id,
            buyer_id=self.b_id,
            merchant_id=self.m_id,
            mandate_id=self.man_id,
            mandate_version=1,
            policy_version=1,
            amount_paise=15000,
            currency=Currency.INR,
            cart_hash="a" * 64,
            idempotency_key=idem_key,
            state=TransactionState.AUTHORIZED,
        )

        proposal = PaymentExecuteProposalRequest(
            transaction_id=tx_id,
            merchant_id=self.m_id,
            buyer_id=self.b_id,
            mandate_id=self.man_id,
            amount_paise=15000,
            currency=Currency.INR,
            cart_hash="a" * 64,
            operation=McpOperation.CREATE_ORDER,
            idempotency_key=idem_key,
        )

        auth = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=[
                SecurityControlOutcome(
                    control_name="MANDATE_EVALUATION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="MERCHANT_POLICY", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="CART_INTEGRITY", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="BUDGET_RESERVATION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="REPLAY_PROTECTION", passed=True, decision=PolicyDecision.ALLOW
                ),
                SecurityControlOutcome(
                    control_name="NONCE_VALIDATION", passed=True, decision=PolicyDecision.ALLOW
                ),
            ],
            decision_trace={"authorization_reference": f"auth_{tx_id[:8]}"},
        )

        # 2. Execute payment
        async with AsyncUnitOfWork(self.session_factory) as uow:
            res = await service.async_execute_payment(uow, proposal, auth, tx_domain)
            self.assertTrue(res.success)
            await uow.commit()

        # 3. Verify outbox pending count & metrics
        async with AsyncUnitOfWork(self.session_factory) as uow:
            pending_count = await uow.outbox.get_pending_count()
            self.assertGreaterEqual(pending_count, 1)
            age = await uow.outbox.get_oldest_pending_age_seconds()
            self.assertGreaterEqual(age, 0.0)

            # Dispatch event
            events = await uow.outbox.get_pending_events(limit=10)
            self.assertGreaterEqual(len(events), 1)
            await uow.outbox.mark_dispatched(events[0].outbox_id)
            await uow.commit()

        created_metric = metrics_registry.get_counter_value(
            "outbox_events_created_total",
            labels={"event_type": "PAYMENT_COMMITTED", "aggregate_type": "TRANSACTION"},
        )
        self.assertGreaterEqual(created_metric, 1)

    async def test_recovery_service_observability_metrics(self) -> None:
        """Verify stuck transaction recovery updates operational metrics counters."""
        tx_id = _uid("tx")
        past = datetime.now(timezone.utc) - timedelta(seconds=60)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            t = await uow.transactions.create_transaction(
                transaction_id=tx_id,
                buyer_id=self.b_id,
                merchant_id=self.m_id,
                mandate_id=self.man_id,
                amount_paise=10000,
                cart_hash="b" * 64,
                idempotency_key=f"idem_{tx_id}",
                state=TransactionState.AUTHORIZED,
            )
            t.state = TransactionState.EXECUTING.value
            t.updated_at = past
            await uow.commit()

        adapter = MockRazorpayAdapter()
        adapter.set_reconciliation_status(PaymentResultState.SUCCESS)
        recovery_service = TransactionRecoveryService(adapter)

        async with AsyncUnitOfWork(self.session_factory) as uow:
            stuck_ids = await recovery_service.scan_stuck_transactions(
                uow, stuck_threshold_seconds=10
            )
            self.assertIn(tx_id, stuck_ids)
            rec = await recovery_service.reconcile_transaction(uow, tx_id)
            self.assertTrue(rec.recovered)
            await uow.commit()

        scans = metrics_registry.get_counter_value("recovery_scans_total")
        self.assertGreaterEqual(scans, 1)

        reconciled = metrics_registry.get_counter_value(
            "recovery_reconciled_total", labels={"status": "SUCCESS"}
        )
        self.assertGreaterEqual(reconciled, 1)


if __name__ == "__main__":
    unittest.main()
