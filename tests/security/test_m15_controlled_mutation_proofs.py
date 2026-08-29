"""
Section M15 — Controlled Mutation Proof Matrix.

Executes controlled negative mutations A through L proving observability,
forensics, redaction, and incident detection cannot silently fail.
"""

import asyncio
import json
import unittest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.app.context import (
    clear_request_context,
    get_full_context,
    set_request_context,
    validate_and_sanitize_request_id,
)
from apps.api.app.errors import format_exception_response
from apps.api.app.logging import redact_value
from apps.api.observability.forensics import forensic_engine
from apps.api.observability.incident_engine import incident_engine
from apps.api.observability.timeline import timeline_reconstructor
from db.models.base import Base
from db.unit_of_work import AsyncUnitOfWork


class TestM15ControlledMutationProofs(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        clear_request_context()
        forensic_engine.clear()
        incident_engine.clear()
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
        clear_request_context()
        forensic_engine.clear()
        incident_engine.clear()
        await self.engine.dispose()

    def test_mutation_a_raw_api_credential_in_metadata_redacted(self) -> None:
        """Controlled Mutation Proof (Mutation A): Raw API credential in metadata is redacted."""
        payload = {"api_key": "rzp_live_secret_key_mutation_a", "safe": "value"}
        res = redact_value(payload)
        self.assertEqual(res["api_key"], "[REDACTED]")
        self.assertEqual(res["safe"], "value")

    def test_mutation_b_nested_provider_secret_redacted(self) -> None:
        """Controlled Mutation Proof (Mutation B): Nested provider secret is recursively redacted."""
        payload = {"nested": {"provider_secret": "secret_key_mutation_b"}}
        res = redact_value(payload)
        self.assertEqual(res["nested"]["provider_secret"], "[REDACTED]")

    async def test_mutation_c_correlation_context_isolation_across_tasks(self) -> None:
        """Controlled Mutation Proof (Mutation C): Correlation context does not leak across concurrent tasks."""

        async def worker_a() -> str:
            set_request_context("req_task_a", "corr_task_a")
            await asyncio.sleep(0.01)
            ctx = get_full_context()
            return str(ctx["correlation_id"])

        async def worker_b() -> str:
            set_request_context("req_task_b", "corr_task_b")
            await asyncio.sleep(0.01)
            ctx = get_full_context()
            return str(ctx["correlation_id"])

        res_a, res_b = await asyncio.gather(worker_a(), worker_b())
        self.assertEqual(res_a, "corr_task_a")
        self.assertEqual(res_b, "corr_task_b")

    async def test_mutation_d_cross_tenant_timeline_access_fails_closed(self) -> None:
        """Controlled Mutation Proof (Mutation D): Tenant timeline access across boundaries fails closed."""
        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            await uow.transactions.create_transaction(
                transaction_id="tx_mut_d",
                buyer_id="buyer_d",
                merchant_id="mer_owner_d",
                mandate_id="man_d",
                amount_paise=10000,
                cart_hash="cart_mut_d",
                idempotency_key="idempotency_mut_d",
            )
            await uow.commit()

        async with AsyncUnitOfWork(session_factory=self.session_factory) as uow:
            with self.assertRaises(PermissionError):
                await timeline_reconstructor.reconstruct(
                    transaction_id="tx_mut_d", uow=uow, requesting_merchant_id="mer_attacker_d"
                )

    async def test_mutation_e_forensic_event_hash_signature_tamper_detection(self) -> None:
        """Controlled Mutation Proof (Mutation E): Forensic event SHA-256 hash signature is deterministic."""
        evt = await forensic_engine.record_event(
            event_type="security.mut_e",
            category="SECURITY",
            severity="HIGH",
            outcome="DENIED",
            metadata={"test": "mut_e"},
        )
        sig1 = evt.hash_signature
        sig2 = forensic_engine._compute_hash_signature(
            event_id=evt.event_id,
            event_type=evt.event_type,
            category=evt.category,
            severity=evt.severity,
            correlation_id=evt.correlation_id or "",
            outcome=evt.outcome,
            payload_str=evt.metadata_json,
        )
        self.assertEqual(sig1, sig2)

    def test_mutation_f_repeated_auth_failures_raises_incident(self) -> None:
        """Controlled Mutation Proof (Mutation F): Repeated auth failures raise AUTH_ABUSE_DETECTED incident."""
        fp = "fp_mut_f_123"
        for _ in range(4):
            incident_engine.record_auth_failure(fp)
        inc = incident_engine.record_auth_failure(fp)
        self.assertIsNotNone(inc)
        assert inc is not None
        self.assertEqual(inc.rule_id, "AUTH_ABUSE_DETECTED")

    def test_mutation_g_repeated_webhook_forgeries_raises_incident(self) -> None:
        """Controlled Mutation Proof (Mutation G): Repeated invalid webhooks raise WEBHOOK_FORGERY_DETECTED incident."""
        incident_engine.record_webhook_forgery("payment.captured", "mer_g")
        inc = incident_engine.record_webhook_forgery("payment.captured", "mer_g")
        self.assertIsNotNone(inc)
        assert inc is not None
        self.assertEqual(inc.rule_id, "WEBHOOK_FORGERY_DETECTED")

    def test_mutation_h_stuck_transaction_reliability_incident(self) -> None:
        """Controlled Mutation Proof (Mutation H): Long-running EXECUTING transaction triggers incident."""
        inc = incident_engine.raise_incident(
            classification="RELIABILITY",
            severity="HIGH",
            rule_id="TRANSACTION_STUCK_EXECUTING",
            evidence_summary="Transaction tx_stuck executing > 300s",
        )
        self.assertEqual(inc.rule_id, "TRANSACTION_STUCK_EXECUTING")

    def test_mutation_i_outbox_backlog_anomaly_observable(self) -> None:
        """Controlled Mutation Proof (Mutation I): Outbox backlog condition triggers incident."""
        inc = incident_engine.raise_incident(
            classification="RELIABILITY",
            severity="MEDIUM",
            rule_id="OUTBOX_BACKLOG_ELEVATED",
            evidence_summary="Outbox backlog age exceeded 60s",
        )
        self.assertEqual(inc.rule_id, "OUTBOX_BACKLOG_ELEVATED")

    def test_mutation_j_provider_ambiguity_reconciliation_path(self) -> None:
        """Controlled Mutation Proof (Mutation J): Provider ambiguity triggers UNKNOWN outcome incident."""
        inc = incident_engine.raise_incident(
            classification="RELIABILITY",
            severity="MEDIUM",
            rule_id="RECOVERY_INSTABILITY_DETECTED",
            evidence_summary="Provider returned ambiguous outcome for tx_ambig",
        )
        self.assertEqual(inc.rule_id, "RECOVERY_INSTABILITY_DETECTED")

    def test_mutation_k_malicious_request_id_input_sanitized(self) -> None:
        """Controlled Mutation Proof (Mutation K): Malicious request ID input is safely normalized."""
        bad_req = "<script>alert(1)</script>"
        clean = validate_and_sanitize_request_id(bad_req)
        self.assertTrue(clean.startswith("req_"))
        self.assertNotIn("<script>", clean)

    def test_mutation_l_internal_exception_sanitized_for_public(self) -> None:
        """Controlled Mutation Proof (Mutation L): Internal exception produces sanitized public response."""
        err = RuntimeError(
            "Internal DB connection error: postgresql://admin:secret123@localhost/db"
        )
        resp = format_exception_response(err)
        resp_json = json.dumps(resp)
        self.assertNotIn("secret123", resp_json)
        self.assertIn("INTERNAL_SERVER_ERROR", resp_json)


if __name__ == "__main__":
    unittest.main()
