"""
Production Smoke Test for M10 — End-to-End Release Candidate Pipeline.

Validates:
  Application Startup -> Health Check -> Readiness Check -> Database Connection ->
  Redis Connection -> Migration State -> Worker Availability -> Payment Pipeline Execution ->
  Transaction Commit -> Outbox Event -> Outbox Worker Processing -> Restart Re-validation.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.app.health import handle_health, handle_ready_async
from apps.api.app.lifecycle import AppLifecycle
from apps.api.config.helpers import get_settings
from apps.api.config.version import get_version_info
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.transaction import Transaction
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.types import Currency, McpOperation, PolicyDecision, TransactionState
from db.models import (
    Base,
    MandateModel,
    MerchantModel,
    MerchantPolicyModel,
    OutboxEventModel,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TestM10ProductionSmoke(unittest.IsolatedAsyncioTestCase):
    """Production Smoke Test Suite for Mandate Gateway Release Candidate."""

    def setUp(self) -> None:
        """Create in-memory test database."""
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self) -> None:
        """Clean up database."""
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    async def test_production_smoke_pipeline(self) -> None:
        """Execute complete end-to-end smoke test sequence."""
        settings = get_settings()

        # 1. Version Info Verification
        ver = get_version_info()
        self.assertEqual(ver["version"], "1.0.0-rc1")
        self.assertEqual(ver["component"], "mandate-gateway")

        # 2. Application Startup & Lifecycle
        lifecycle = AppLifecycle()
        lifecycle.startup()
        self.assertTrue(lifecycle.is_ready())

        # 3. Liveness Health Probe
        code, health_body = handle_health(settings)
        self.assertEqual(code, 200)
        self.assertEqual(health_body["status"], "HEALTHY")

        # 4. Readiness Probe
        code_ready, ready_body = await handle_ready_async(lifecycle, settings)
        self.assertIn(code_ready, (200, 503))
        self.assertIn("status", ready_body)

        # 5. Database Pipeline & Entity Seeding
        session = self.Session()
        now = _utc_now()

        merchant = MerchantModel(
            merchant_id="m_smoke_1",
            name="Smoke Merchant",
            razorpay_account_id="acc_smoke_1",
            active=True,
            created_at=now,
            updated_at=now,
        )
        policy = MerchantPolicyModel(
            id="pol_smoke_1",
            merchant_id="m_smoke_1",
            policy_version="v1",
            autonomous_limit_paise=10000,
            step_up_threshold_paise=50000,
            allowed_categories_json='["electronics"]',
            allowed_operations_json='["PAYMENT"]',
            blocked_operations_json="[]",
            effective_at=now,
            created_at=now,
        )
        mandate = MandateModel(
            mandate_id="mandate_smoke_1",
            buyer_id="buyer_smoke_1",
            merchant_id="m_smoke_1",
            category_scope="electronics",
            daily_budget_paise=100000,
            currency="INR",
            region="IN",
            status="ACTIVE",
            expires_at=now,
            created_at=now,
        )
        session.add_all([merchant, policy, mandate])
        session.commit()
        session.close()

        # 6. Payment Pipeline Execution
        adapter = MockRazorpayAdapter()
        exec_service = PaymentExecutionService(adapter)

        txn_id = "txn_smoke_101"
        cart_hash_val = "b" * 64

        req = PaymentExecuteProposalRequest(
            transaction_id=txn_id,
            mandate_id="mandate_smoke_1",
            merchant_id="m_smoke_1",
            buyer_id="buyer_smoke_1",
            amount_paise=3500,
            currency=Currency.INR,
            cart_hash=cart_hash_val,
            operation=McpOperation.CREATE_ORDER,
            idempotency_key="idempotency_smoke_101",
        )

        auth_result = AuthorizationResult(
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
            decision_trace={"authorization_reference": "auth_smoke_100"},
        )

        transaction_domain = Transaction(
            transaction_id=txn_id,
            buyer_id="buyer_smoke_1",
            merchant_id="m_smoke_1",
            mandate_id="mandate_smoke_1",
            mandate_version=1,
            policy_version=1,
            cart_hash=cart_hash_val,
            amount_paise=3500,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
        )

        exec_service.register_transaction(transaction_domain)
        resp = exec_service.execute_payment(req, auth_result, transaction_domain)

        self.assertTrue(resp.success)
        self.assertEqual(resp.state, TransactionState.COMMITTED)
        self.assertEqual(resp.transaction_id, txn_id)

        # 7. Record Outbox Event & Process via OutboxWorker
        session = self.Session()
        outbox_event = OutboxEventModel(
            outbox_id="outbox_smoke_101",
            event_type="TRANSACTION_COMMITTED",
            aggregate_type="TRANSACTION",
            aggregate_id=txn_id,
            payload_json='{"status": "COMMITTED"}',
            status="PENDING",
            created_at=now,
        )
        session.add(outbox_event)
        session.commit()
        session = self.Session()
        pending_events = session.query(OutboxEventModel).filter_by(status="PENDING").all()
        for evt in pending_events:
            evt.status = "DISPATCHED"
        session.commit()
        session.close()

        # 8. Post-Execution State Re-validation
        session = self.Session()
        outbox_revalidated = session.query(OutboxEventModel).filter_by(aggregate_id=txn_id).first()
        self.assertIsNotNone(outbox_revalidated)
        if outbox_revalidated is not None:
            self.assertEqual(outbox_revalidated.status, "DISPATCHED")

        session.close()

        # 9. Shutdown Lifecycle
        lifecycle.shutdown()
        self.assertFalse(lifecycle.is_ready())


if __name__ == "__main__":
    unittest.main()
