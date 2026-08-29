"""
S05.5 — End-to-End Production Integration & Persistence Test Suite.

Verifies end-to-end persistent call paths across all domain engines, repositories,
AsyncUnitOfWork boundaries, action receipt persistence, and audit ledger hash chaining.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.adapters.razorpay_adapter import MockRazorpayAdapter
from apps.api.contracts.authorization import AuthorizationResult
from apps.api.contracts.execution import PaymentExecuteProposalRequest
from apps.api.domain.audit import GENESIS_HASH
from apps.api.domain.budget_engine import BudgetEngine
from apps.api.domain.execution_engine import PaymentExecutionService
from apps.api.domain.intent import CommerceIntent
from apps.api.domain.mandate_lifecycle import (
    async_create_mandate,
    async_get_mandate,
    async_transition_mandate,
)
from apps.api.domain.merchant_policy_engine import MerchantPolicyEngine
from apps.api.domain.nonce_engine import NonceEngine
from apps.api.domain.receipt_signer import ActionReceiptSigner, Ed25519KeyManager
from apps.api.domain.receipt_verifier import ReceiptVerifier
from apps.api.domain.replay_engine import ReplayProtectionEngine
from apps.api.domain.step_up import StepUpChallengeStatus
from apps.api.domain.step_up_engine import StepUpEngine, TrustedConfirmation
from apps.api.domain.transaction import Transaction
from apps.api.domain.types import (
    AuditEventType,
    BudgetState,
    Currency,
    MandateStatus,
    McpOperation,
    NonceState,
    PolicyDecision,
    TransactionState,
)
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestM055E2EPersistence(unittest.IsolatedAsyncioTestCase):
    """End-to-End Persistence Integration Test Suite for S05.5."""

    async def asyncSetUp(self) -> None:
        """Initialize in-memory SQLite engine and session factory."""
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
        """Dispose engine resources."""
        await self.engine.dispose()

    # ------------------------------------------------------------------
    # Scenario A — Merchant & Policy Persistence
    # ------------------------------------------------------------------
    async def test_scenario_a_merchant_policy_persistence(self) -> None:
        """Verify merchant policy creation, persistence, fresh session retrieval, and evaluation."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            m = await uow.merchants.create_merchant("mer_e2e_1", "E2E Merchant", "acc_e2e_1")
            await uow.merchants.create_policy(
                policy_id="pol_e2e_1",
                merchant_id=m.merchant_id,
                policy_version="1",
                autonomous_limit_paise=500000,  # ₹5,000
                step_up_threshold_paise=400000,
                allowed_categories=["electronics", "books"],
                allowed_operations=["create_order", "fetch_payment"],
                blocked_operations=["payout", "bank_transfer"],
                active=True,
            )
            await uow.commit()

        # Reload from fresh UoW session
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            policy = await MerchantPolicyEngine.async_get_active_policy(uow, "mer_e2e_1")
            self.assertIsNotNone(policy)
            assert policy is not None
            self.assertEqual(policy.merchant_id, "mer_e2e_1")
            self.assertTrue(policy.ai_commerce_enabled)
            self.assertEqual(policy.autonomous_purchase_limit_paise, 500000)
            self.assertIn("electronics", policy.allowed_categories)

            intent = CommerceIntent(
                buyer_id="buyer_1",
                raw_prompt="buy electronics",
                target_merchant_id="mer_e2e_1",
                target_category="electronics",
                max_budget_paise=150000,
                currency=Currency.INR,
            )
            res = await MerchantPolicyEngine.async_evaluate(uow, "mer_e2e_1", intent)
            self.assertEqual(res.decision, PolicyDecision.ALLOW)

    # ------------------------------------------------------------------
    # Scenario B — Mandate Lifecycle Persistence
    # ------------------------------------------------------------------
    async def test_scenario_b_mandate_lifecycle_persistence(self) -> None:
        """Verify buyer mandate creation, row lock status transition, and fresh session retrieval."""
        exp = datetime.now(tz=timezone.utc) + timedelta(days=7)
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            mandate = await async_create_mandate(
                uow,
                mandate_id="man_e2e_1",
                buyer_id="buyer_e2e_1",
                daily_budget_paise=2000000,  # ₹20,000
                expires_at=exp,
                merchant_id="mer_e2e_1",
                status=MandateStatus.ACTIVE,
            )
            await uow.commit()
            self.assertEqual(mandate.status, MandateStatus.ACTIVE)

        # Transition status under lock in fresh session
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            updated = await async_transition_mandate(uow, "man_e2e_1", MandateStatus.SUSPENDED)
            await uow.commit()
            self.assertEqual(updated.status, MandateStatus.SUSPENDED)

        # Verify fresh session reload
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            reloaded = await async_get_mandate(uow, "man_e2e_1")
            self.assertIsNotNone(reloaded)
            assert reloaded is not None
            self.assertEqual(reloaded.status, MandateStatus.SUSPENDED)

    # ------------------------------------------------------------------
    # Scenario C — Budget Reservation & Overspend Prevention
    # ------------------------------------------------------------------
    async def test_scenario_c_budget_reservation_overspend_prevention(self) -> None:
        """Verify atomic budget reservation, overspend rejection, and release restoration."""
        exp = datetime.now(tz=timezone.utc) + timedelta(days=1)
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.merchants.create_merchant("mer_bgt_e2e", "Budget E2E Merchant")
            await uow.mandates.create_mandate(
                mandate_id="man_bgt_e2e",
                buyer_id="buyer_bgt",
                daily_budget_paise=100000,  # ₹1,000 limit
                expires_at=exp,
                merchant_id="mer_bgt_e2e",
            )
            await uow.commit()

        engine = BudgetEngine()
        # 1. Successful reservation (60000 paise)
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            tx1 = await uow.transactions.create_transaction(
                transaction_id="tx_bgt_1",
                buyer_id="buyer_bgt",
                merchant_id="mer_bgt_e2e",
                mandate_id="man_bgt_e2e",
                amount_paise=60000,
                cart_hash="a" * 64,
                idempotency_key="idemp_bgt_1",
            )
            res1 = await engine.async_reserve(
                uow,
                mandate_id="man_bgt_e2e",
                transaction_id=tx1.transaction_id,
                amount_paise=60000,
                currency=Currency.INR,
                reservation_id="res_1",
            )
            await uow.commit()
            self.assertTrue(res1.valid)
            self.assertEqual(res1.decision, PolicyDecision.ALLOW)

        # 2. Overspend attempt (50000 paise > available 40000 paise)
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            tx2 = await uow.transactions.create_transaction(
                transaction_id="tx_bgt_2",
                buyer_id="buyer_bgt",
                merchant_id="mer_bgt_e2e",
                mandate_id="man_bgt_e2e",
                amount_paise=50000,
                cart_hash="b" * 64,
                idempotency_key="idemp_bgt_2",
            )
            res2 = await engine.async_reserve(
                uow,
                mandate_id="man_bgt_e2e",
                transaction_id=tx2.transaction_id,
                amount_paise=50000,
                currency=Currency.INR,
                reservation_id="res_2",
            )
            self.assertFalse(res2.valid)
            self.assertEqual(res2.decision, PolicyDecision.REJECT)

        # 3. Release res_1 restores availability
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            released = await engine.async_release(uow, "man_bgt_e2e", "res_1")
            await uow.commit()
            self.assertEqual(released.state, BudgetState.RELEASED)

    # ------------------------------------------------------------------
    # Scenario D — Step-Up Challenge Approval Persistence
    # ------------------------------------------------------------------
    async def test_scenario_d_step_up_challenge_approval(self) -> None:
        """Verify step-up challenge creation, single-use approval, and double-approval rejection."""
        exp = datetime.now(tz=timezone.utc) + timedelta(days=1)
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.merchants.create_merchant("mer_su", "StepUp Merchant")
            await uow.mandates.create_mandate(
                mandate_id="man_su",
                buyer_id="buyer_su",
                daily_budget_paise=1000000,
                expires_at=exp,
                merchant_id="mer_su",
            )
            await uow.transactions.create_transaction(
                transaction_id="tx_su_1",
                buyer_id="buyer_su",
                merchant_id="mer_su",
                mandate_id="man_su",
                amount_paise=800000,
                cart_hash="c" * 64,
                idempotency_key="idemp_su_1",
            )
            await uow.commit()

        engine = StepUpEngine()
        # Create challenge
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            ch = await engine.async_create_challenge(
                uow,
                mandate_id="man_su",
                transaction_id="tx_su_1",
                cart_hash="c" * 64,
                approved_paise=500000,
                proposed_paise=800000,
                merchant_id="mer_su",
            )
            await uow.commit()
            self.assertIsNotNone(ch)
            self.assertEqual(ch.status, StepUpChallengeStatus.PENDING)

        # Record human confirmation in fresh session
        conf = TrustedConfirmation(
            challenge_id=ch.challenge_id,
            mandate_id="man_su",
            transaction_id="tx_su_1",
            cart_hash="c" * 64,
            proposed_paise=800000,
            merchant_id="mer_su",
            confirmed_by="admin_user",
        )
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            rec1 = await engine.async_record_human_confirmation(uow, conf)
            await uow.commit()
            self.assertEqual(rec1.status, StepUpChallengeStatus.APPROVED)

        # Double approval attempt fails
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            with self.assertRaises(ValueError):
                await engine.async_record_human_confirmation(uow, conf)

    # ------------------------------------------------------------------
    # Scenario E — Replay Protection Persistence
    # ------------------------------------------------------------------
    async def test_scenario_e_replay_protection_persistence(self) -> None:
        """Verify payload fingerprint registration and duplicate replay rejection in fresh session."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.merchants.create_merchant("mer_rp", "Replay Merchant")
            await uow.mandates.create_mandate(
                mandate_id="man_rp",
                buyer_id="buyer_rp",
                daily_budget_paise=1000000,
                expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
                merchant_id="mer_rp",
            )
            await uow.transactions.create_transaction(
                transaction_id="tx_rp_1",
                buyer_id="buyer_rp",
                merchant_id="mer_rp",
                mandate_id="man_rp",
                amount_paise=10000,
                cart_hash="d" * 64,
                idempotency_key="idemp_rp_1",
            )
            await uow.commit()

        engine = ReplayProtectionEngine()

        # 1. Register initial request
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            eval1 = await engine.async_check_and_record(
                uow,
                mandate_id="man_rp",
                transaction_id="tx_rp_1",
                cart_hash="d" * 64,
                merchant_id="mer_rp",
            )
            await uow.commit()
            self.assertTrue(eval1.valid)
            self.assertEqual(eval1.decision, PolicyDecision.ALLOW)

        # 2. Duplicate replay attempt in fresh session
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            eval2 = await engine.async_check_and_record(
                uow,
                mandate_id="man_rp",
                transaction_id="tx_rp_1",
                cart_hash="d" * 64,
                merchant_id="mer_rp",
            )
            self.assertFalse(eval2.valid)
            self.assertEqual(eval2.decision, PolicyDecision.REJECT)

    # ------------------------------------------------------------------
    # Scenario F — Nonce Issuance & Single-Use Consumption Persistence
    # ------------------------------------------------------------------
    async def test_scenario_f_nonce_issuance_and_single_use_consumption(self) -> None:
        """Verify nonce issuance, single-use consumption under lock, and double-use rejection."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.merchants.create_merchant("mer_nc", "Nonce Merchant")
            await uow.mandates.create_mandate(
                mandate_id="man_nc",
                buyer_id="buyer_nc",
                daily_budget_paise=1000000,
                expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
                merchant_id="mer_nc",
            )
            await uow.transactions.create_transaction(
                transaction_id="tx_nc_1",
                buyer_id="buyer_nc",
                merchant_id="mer_nc",
                mandate_id="man_nc",
                amount_paise=20000,
                cart_hash="e" * 64,
                idempotency_key="idemp_nc_1",
            )
            await uow.commit()

        engine = NonceEngine()
        # Issue nonce
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            rec = await engine.async_issue_nonce(uow, mandate_id="man_nc", transaction_id="tx_nc_1")
            await uow.commit()
            self.assertEqual(rec.state, NonceState.ISSUED)

        # Consume nonce
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            res1 = await engine.async_validate_and_consume(
                uow,
                nonce_value=rec.nonce_value,
                mandate_id="man_nc",
                transaction_id="tx_nc_1",
            )
            await uow.commit()
            self.assertTrue(res1.valid)
            self.assertEqual(res1.decision, PolicyDecision.ALLOW)

        # Double-consumption attempt fails closed
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            res2 = await engine.async_validate_and_consume(
                uow,
                nonce_value=rec.nonce_value,
                mandate_id="man_nc",
                transaction_id="tx_nc_1",
            )
            self.assertFalse(res2.valid)
            self.assertEqual(res2.decision, PolicyDecision.REJECT)

    # ------------------------------------------------------------------
    # Scenario G — Transaction 3-Step Execution Persistence
    # ------------------------------------------------------------------
    async def test_scenario_g_transaction_3_step_execution_persistence(self) -> None:
        """Verify 3-step DB-bound payment execution, provider dispatch, and outcome persistence."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.merchants.create_merchant("mer_exec", "Exec Merchant")
            await uow.mandates.create_mandate(
                mandate_id="man_exec",
                buyer_id="buyer_exec",
                daily_budget_paise=1000000,
                expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
                merchant_id="mer_exec",
            )
            await uow.transactions.create_transaction(
                transaction_id="tx_exec_1",
                buyer_id="buyer_exec",
                merchant_id="mer_exec",
                mandate_id="man_exec",
                amount_paise=30000,
                cart_hash="f" * 64,
                idempotency_key="idemp_exec_1",
                state=TransactionState.AUTHORIZED,
            )
            await uow.commit()

        # Mock adapter
        adapter = MockRazorpayAdapter()
        engine = PaymentExecutionService(adapter=adapter)

        domain_tx = Transaction(
            transaction_id="tx_exec_1",
            buyer_id="buyer_exec",
            merchant_id="mer_exec",
            mandate_id="man_exec",
            mandate_version=1,
            policy_version=1,
            amount_paise=30000,
            currency=Currency.INR,
            state=TransactionState.AUTHORIZED,
            cart_hash="f" * 64,
            idempotency_key="idemp_exec_1",
        )
        proposal = PaymentExecuteProposalRequest(
            transaction_id="tx_exec_1",
            merchant_id="mer_exec",
            mandate_id="man_exec",
            buyer_id="buyer_exec",
            amount_paise=30000,
            currency=Currency.INR,
            operation=McpOperation.CREATE_ORDER,
            cart_hash="f" * 64,
            idempotency_key="idemp_exec_1",
        )
        from apps.api.domain.authorization_aggregator import SecurityControlOutcome

        ctrls = [
            SecurityControlOutcome(
                control_name="MANDATE_EVALUATION", decision=PolicyDecision.ALLOW, passed=True
            ),
            SecurityControlOutcome(
                control_name="MERCHANT_POLICY", decision=PolicyDecision.ALLOW, passed=True
            ),
            SecurityControlOutcome(
                control_name="CART_INTEGRITY", decision=PolicyDecision.ALLOW, passed=True
            ),
            SecurityControlOutcome(
                control_name="BUDGET_RESERVATION", decision=PolicyDecision.ALLOW, passed=True
            ),
            SecurityControlOutcome(
                control_name="REPLAY_PROTECTION", decision=PolicyDecision.ALLOW, passed=True
            ),
            SecurityControlOutcome(
                control_name="NONCE_VALIDATION", decision=PolicyDecision.ALLOW, passed=True
            ),
        ]
        auth_res = AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            control_outcomes=ctrls,
            decision_trace={"authorization_reference": "auth_exec_123"},
        )

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            res = await engine.async_execute_payment(uow, proposal, auth_res, domain_tx)
            await uow.commit()
            self.assertTrue(res.success)
            self.assertEqual(res.state, TransactionState.COMMITTED)

        # Verify DB transaction state
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            db_tx = await uow.transactions.get_transaction("tx_exec_1")
            self.assertIsNotNone(db_tx)
            assert db_tx is not None
            self.assertEqual(db_tx.state, TransactionState.COMMITTED.value)

    # ------------------------------------------------------------------
    # Scenario H — Action Receipt Persistence & Ed25519 Verification
    # ------------------------------------------------------------------
    async def test_scenario_h_action_receipt_persistence_and_verification(self) -> None:
        """Verify ActionReceipt creation, Ed25519 signature persistence, and DB reload verification."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.merchants.create_merchant("mer_rcpt", "Receipt Merchant")
            await uow.mandates.create_mandate(
                mandate_id="man_rcpt",
                buyer_id="buyer_rcpt",
                daily_budget_paise=1000000,
                expires_at=datetime.now(tz=timezone.utc) + timedelta(days=1),
                merchant_id="mer_rcpt",
            )
            await uow.transactions.create_transaction(
                transaction_id="tx_rcpt_1",
                buyer_id="buyer_rcpt",
                merchant_id="mer_rcpt",
                mandate_id="man_rcpt",
                amount_paise=45000,
                cart_hash="1" * 64,
                idempotency_key="idemp_rcpt_1",
            )
            audit_model = await uow.audit.append_event(
                event_type=AuditEventType.PAYMENT_SUCCESS,
                transaction_id="tx_rcpt_1",
                mandate_id="man_rcpt",
                merchant_id="mer_rcpt",
                buyer_id="buyer_rcpt",
                payload={"payment_id": "pay_rcpt_111"},
            )
            await uow.commit()
            audit_id = audit_model.event_id

        # Sign ActionReceipt using Ed25519 key manager
        key_mgr = Ed25519KeyManager.generate()
        signer = ActionReceiptSigner(key_manager=key_mgr)

        receipt = signer.sign_receipt(
            transaction_id="tx_rcpt_1",
            mandate_id="man_rcpt",
            merchant_id="mer_rcpt",
            policy_version=1,
            cart_hash="1" * 64,
            amount_paise=45000,
            currency=Currency.INR,
            decision=PolicyDecision.ALLOW,
            execution_tool="razorpay_create_order",
            execution_reference="pay_rcpt_111",
            audit_hash=audit_model.event_hash,
            receipt_id="rcpt_e2e_1",
        )

        # Persist receipt to database via ReceiptRepository
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            model = await uow.receipts.create_receipt(
                receipt_id=receipt.receipt_id,
                transaction_id="tx_rcpt_1",
                audit_event_id=audit_id,
                canonical_payload_hash=receipt.canonical_payload_hash,
                signature_hex=receipt.signature or "",
                public_key_hex=key_mgr.get_public_key_hex(),
            )
            await uow.commit()
            self.assertEqual(model.receipt_id, "rcpt_e2e_1")

        # Reload from fresh session and verify Ed25519 signature
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            db_receipt = await uow.receipts.get_receipt("rcpt_e2e_1")
            self.assertIsNotNone(db_receipt)
            assert db_receipt is not None
            self.assertEqual(db_receipt.canonical_payload_hash, receipt.canonical_payload_hash)

            # Perform cryptographic verification
            v_res = ReceiptVerifier.verify(receipt, key_mgr.public_key)
            self.assertTrue(v_res.is_valid)

    # ------------------------------------------------------------------
    # Scenario I — Audit Hash Chain Continuity & Verification
    # ------------------------------------------------------------------
    async def test_scenario_i_audit_hash_chain_continuity(self) -> None:
        """Verify sequential audit event appends, sequence numbers, SHA-256 hash chaining, and integrity check."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            evt1 = await uow.audit.append_event(
                event_type=AuditEventType.MANDATE_CREATED,
                mandate_id="man_audit_1",
                buyer_id="buyer_audit",
                payload={"limit_paise": 500000},
            )
            evt2 = await uow.audit.append_event(
                event_type=AuditEventType.CART_PROPOSED,
                transaction_id="tx_audit_1",
                mandate_id="man_audit_1",
                payload={"cart_total": 120000},
            )
            evt3 = await uow.audit.append_event(
                event_type=AuditEventType.PAYMENT_SUCCESS,
                transaction_id="tx_audit_1",
                payload={"payment_id": "pay_audit_123"},
            )
            await uow.commit()

            self.assertEqual(evt1.sequence_number, 1)
            self.assertEqual(evt1.previous_hash, GENESIS_HASH)
            self.assertEqual(evt2.sequence_number, 2)
            self.assertEqual(evt2.previous_hash, evt1.event_hash)
            self.assertEqual(evt3.sequence_number, 3)
            self.assertEqual(evt3.previous_hash, evt2.event_hash)

        # Verify hash chain integrity in fresh session
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            is_valid, err = await uow.audit.verify_chain()
            self.assertTrue(is_valid, msg=err)


if __name__ == "__main__":
    unittest.main()
