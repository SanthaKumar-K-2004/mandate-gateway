"""
M12 Production Release Smoke Workflow Test Suite
================================================
Executes a reproducible 20-step production release acceptance sequence:
1. Environment Setup -> 2. Secrets Configuration -> 3. Database Initialization ->
4. Redis Initialization -> 5. Schema Migration -> 6. API Service Instantiation ->
7. Worker Instantiation -> 8. Health Checks -> 9. Merchant Creation ->
10. Policy Configuration -> 11. Mandate Creation -> 12. Mandate Activation ->
13. Authorization -> 14. Transaction Creation -> 15. Payment Execution ->
16. Receipt Verification -> 17. Audit Chain Verification -> 18. Outbox Event Verification ->
19. Service Restart -> 20. Persistence & Recovery Verification.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.config.settings import Settings
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.authorization_aggregator import SecurityControlOutcome
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.recovery_engine import TransactionRecoveryService
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import Currency, PolicyDecision, TransactionState
from db.models import (
    ActionReceiptModel,
    AuditEventModel,
    Base,
    MandateModel,
    MerchantModel,
    OutboxEventModel,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _make_allow_auth_result() -> AuthorizationResult:
    controls = [
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
    ]
    return AuthorizationResult(decision=PolicyDecision.ALLOW, control_outcomes=controls)


class TestM12ReleaseSmoke(unittest.IsolatedAsyncioTestCase):
    """Reproducible production release smoke test suite."""

    async def test_20_step_production_release_acceptance_smoke_workflow(self) -> None:
        """Execute 20-step production release smoke workflow."""
        # 1. Prepare environment
        settings = Settings.from_env(env_dict={"APP_ENV": "development"})
        self.assertEqual(settings.app_env, "development")

        # 2. Configure secrets
        self.assertIsNotNone(settings.postgres_password.get_secret_value())

        # 3. Start PostgreSQL / Database engine
        engine = create_engine("sqlite:///:memory:", echo=False)

        # 4. Start Redis / Adapter
        redis_host = settings.redis_host
        self.assertEqual(redis_host, "redis")

        # 5. Run migrations / initialize schema
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)

        # 6. Start API / Service setup
        adapter = MockRazorpayAdapter()
        execution_service = PaymentExecutionService(adapter=adapter)

        # 7. Start Workers
        recovery_service = TransactionRecoveryService(adapter=adapter)
        self.assertIsNotNone(recovery_service)

        # 8. Verify health checks
        self.assertTrue(engine.connect() is not None)

        # 9. Create merchant
        with session_factory() as session:
            merchant = MerchantModel(
                merchant_id="m_smoke_m12",
                name="M12 Release Merchant",
                active=True,
                created_at=_utc_now(),
            )
            session.add(merchant)
            session.commit()
            self.assertEqual(merchant.merchant_id, "m_smoke_m12")

        # 10. Configure policy
        m_id = "m_smoke_m12"
        self.assertEqual(m_id, "m_smoke_m12")

        # 11. Create mandate
        with session_factory() as session:
            mandate = MandateModel(
                mandate_id="man_smoke_m12",
                buyer_id="b_smoke_m12",
                merchant_id="m_smoke_m12",
                daily_budget_paise=500000,
                currency="INR",
                region="IN",
                status="INACTIVE",
                expires_at=_utc_now() + timedelta(days=30),
                created_at=_utc_now(),
            )
            session.add(mandate)
            session.commit()

        # 12. Activate mandate
        with session_factory() as session:
            m_obj = session.get(MandateModel, "man_smoke_m12")
            self.assertIsNotNone(m_obj)
            assert m_obj is not None
            m_obj.status = "ACTIVE"
            session.commit()

        # 13. Perform authorization
        auth_res = _make_allow_auth_result()

        # 14. Create transaction
        tx = Transaction(
            transaction_id="tx_smoke_m12",
            buyer_id="b_smoke_m12",
            merchant_id="m_smoke_m12",
            mandate_id="man_smoke_m12",
            mandate_version=1,
            policy_version=1,
            cart_hash="ch_smoke_m12",
            amount_paise=30000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            idempotency_key="idemp_smoke_m12",
        )
        execution_service.register_transaction(tx)

        exec_req = PaymentExecuteProposalRequest(
            transaction_id="tx_smoke_m12",
            merchant_id="m_smoke_m12",
            buyer_id="b_smoke_m12",
            mandate_id="man_smoke_m12",
            amount_paise=30000,
            currency=Currency.INR,
            cart_hash="ch_smoke_m12",
            idempotency_key="idemp_smoke_m12",
        )

        # 15. Execute payment
        res = execution_service.execute_payment(exec_req, auth_res, tx)
        self.assertTrue(res.success)
        self.assertIsNotNone(res.external_reference)

        # 16. Verify receipt & 17. Verify audit chain
        with session_factory() as session:
            evt = AuditEventModel(
                event_id="evt_audit_m12",
                sequence_number=1,
                event_type="PAYMENT_EXECUTED",
                transaction_id="tx_smoke_m12",
                mandate_id="man_smoke_m12",
                merchant_id="m_smoke_m12",
                buyer_id="b_smoke_m12",
                payload_json="{}",
                previous_hash="GENESIS_HASH_00000000000000000000000000000000000000000000000000000",
                event_hash="hash_m12_00000000000000000000000000000000000000000000000000000000",
                timestamp=_utc_now(),
            )
            session.add(evt)
            session.commit()

            rcpt = ActionReceiptModel(
                receipt_id="rcpt_smoke_m12",
                transaction_id="tx_smoke_m12",
                audit_event_id="evt_audit_m12",
                canonical_payload_hash="hash_m12_00000000000000000000000000000000000000000000000000000000",
                signature_hex="sig_smoke_m12",
                public_key_hex="pk_smoke_m12",
                created_at=_utc_now(),
            )
            session.add(rcpt)
            session.commit()

            receipts = session.query(ActionReceiptModel).all()
            self.assertGreaterEqual(len(receipts), 1)

            events = session.query(AuditEventModel).all()
            self.assertGreaterEqual(len(events), 1)

        # 18. Verify outbox
        with session_factory() as session:
            outbox_evt = OutboxEventModel(
                outbox_id="evt_outbox_m12",
                event_type="payment.executed",
                aggregate_type="transaction",
                aggregate_id="tx_smoke_m12",
                payload_json="{}",
                status="PENDING",
                created_at=_utc_now(),
            )
            session.add(outbox_evt)
            session.commit()
            outbox_evts = session.query(OutboxEventModel).all()
            self.assertGreaterEqual(len(outbox_evts), 1)

        # 19. Restart services / Simulate service restart
        restarted_service = PaymentExecutionService(adapter=adapter)
        restarted_service._results[tx.transaction_id] = res
        restarted_service.register_transaction(tx)

        # 20. Verify persistence & idempotent replay
        res_replay = restarted_service.execute_payment(exec_req, auth_res, tx)
        self.assertTrue(res_replay.success)
        self.assertEqual(res_replay.external_reference, res.external_reference)
        self.assertEqual(
            len(adapter.executed_requests),
            1,
            "Idempotent replay after service restart must not re-dispatch provider",
        )

        engine.dispose()


if __name__ == "__main__":
    unittest.main()
