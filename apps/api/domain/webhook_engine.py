"""
S06.3 — Secure Provider Webhook Engine.

Implements the 19-control trust pipeline for external provider webhook processing:
  1. Raw Request Body Authenticity & HMAC SHA-256 Signature Verification
  2. Timestamp Boundary Validation (Anti-Stale / Anti-Future)
  3. Event ID Atomic Deduplication & Replay Protection
  4. Context Binding (Transaction ID & Merchant ID correlation)
  5. State Transition Governance & Terminal State Protection
  6. Append-Only Audit Ledger Linkage
"""

from __future__ import annotations

import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import NamedTuple

from apps.api.config.types import SecretString
from apps.api.domain.audit_ledger import AuditEventType
from apps.api.domain.types import (
    MandateStatus,
    RejectionReason,
    TransactionState,
)
from db.unit_of_work import AsyncUnitOfWork

logger = logging.getLogger("mandate_gateway.webhook_engine")


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


class WebhookProcessingResult(NamedTuple):
    """Normalized response from WebhookEngine processing."""

    success: bool
    event_id: str
    transaction_id: str | None
    state: TransactionState | None
    is_duplicate: bool
    rejection_reason: RejectionReason | None
    rejection_detail: str | None


class WebhookEngine:
    """
    Secure webhook processing engine for external payment provider events.

    Security Controls Enforced:
      1. Signature Verification: Validates HMAC-SHA256 signature against raw payload bytes BEFORE JSON parsing.
      2. Timestamp Boundary: Rejects webhooks with timestamps > 300s in past or > 60s in future.
      3. Event Deduplication: Atomic primary-key event registration in database.
      4. Context Correlation: Validates internal transaction_id and merchant_id match DB records.
      5. State Transition Enforcement: Prevents invalid transitions or terminal state overwrites.
    """

    def __init__(self, webhook_secret: SecretString | str = "whsec_test_secret_key_12345") -> None:
        if isinstance(webhook_secret, SecretString):
            self._webhook_secret = webhook_secret.get_secret_value()
        else:
            self._webhook_secret = str(webhook_secret)

    def verify_signature(self, raw_payload: bytes, signature: str | None) -> bool:
        """
        Verify HMAC SHA-256 signature of raw webhook payload.

        Computed digest: hmac.new(secret, raw_payload, sha256).hexdigest()
        Constant-time comparison via hmac.compare_digest prevents timing attacks.
        """
        if not signature or not signature.strip():
            return False

        computed = hmac.new(
            self._webhook_secret.encode("utf-8"),
            raw_payload,
            hashlib.sha256,
        ).hexdigest()

        clean_sig = signature.strip()
        # Support optional "sha256=" prefix
        if clean_sig.startswith("sha256="):
            clean_sig = clean_sig[7:]

        return hmac.compare_digest(computed.lower(), clean_sig.lower())

    def validate_timestamp(
        self,
        event_timestamp: int | datetime | None,
        now: datetime | None = None,
        max_past_seconds: int = 300,
        max_future_seconds: int = 60,
    ) -> bool:
        """Validate timestamp freshness against current UTC time."""
        if event_timestamp is None:
            return False

        eval_time = now if now is not None else _utc_now()

        if isinstance(event_timestamp, int):
            try:
                event_dt = datetime.fromtimestamp(event_timestamp, tz=timezone.utc)
            except Exception:
                return False
        else:
            event_dt = (
                event_timestamp.replace(tzinfo=timezone.utc)
                if event_timestamp.tzinfo is None
                else event_timestamp
            )

        diff_seconds = (eval_time - event_dt).total_seconds()
        if diff_seconds > max_past_seconds:
            return False  # Stale timestamp
        if diff_seconds < -max_future_seconds:
            return False  # Excessive future timestamp

        return True

    async def async_process_webhook(
        self,
        uow: AsyncUnitOfWork,
        raw_payload: bytes,
        signature: str | None,
        event_id: str | None,
        now: datetime | None = None,
    ) -> WebhookProcessingResult:
        """
        Process incoming provider webhook event through trust pipeline.
        """
        eval_time = now if now is not None else _utc_now()
        payload_hash = hashlib.sha256(raw_payload).hexdigest()

        # Control 1: Raw Signature Verification
        if not self.verify_signature(raw_payload, signature):
            logger.warning("Webhook rejected: Invalid HMAC signature.")
            return WebhookProcessingResult(
                success=False,
                event_id=event_id or "unknown_event",
                transaction_id=None,
                state=None,
                is_duplicate=False,
                rejection_reason=RejectionReason.METHOD_NOT_AUTHORIZED,
                rejection_detail="Webhook signature verification failed (invalid HMAC).",
            )

        # Control 2: Parse Payload JSON
        try:
            payload_data = json.loads(raw_payload.decode("utf-8"))
        except Exception as exc:
            return WebhookProcessingResult(
                success=False,
                event_id=event_id or "unknown_event",
                transaction_id=None,
                state=None,
                is_duplicate=False,
                rejection_reason=RejectionReason.METHOD_NOT_AUTHORIZED,
                rejection_detail=f"Malformed webhook JSON payload: {exc}",
            )

        # Extract Event Attributes
        eff_event_id = (event_id or payload_data.get("id") or "").strip()
        event_type = payload_data.get("event", "payment.unknown").strip()
        event_ts = payload_data.get("created_at")

        if not eff_event_id:
            return WebhookProcessingResult(
                success=False,
                event_id="missing_event_id",
                transaction_id=None,
                state=None,
                is_duplicate=False,
                rejection_reason=RejectionReason.METHOD_NOT_AUTHORIZED,
                rejection_detail="Webhook missing required event identity.",
            )

        # Control 3: Timestamp Freshness
        if event_ts is not None and not self.validate_timestamp(event_ts, now=eval_time):
            return WebhookProcessingResult(
                success=False,
                event_id=eff_event_id,
                transaction_id=None,
                state=None,
                is_duplicate=False,
                rejection_reason=RejectionReason.AUTHORIZATION_EXPIRED,
                rejection_detail="Webhook timestamp outside valid window (stale or excessive future).",
            )

        # Extract Entity Context
        payload_entity = payload_data.get("payload", {}).get("payment", {}).get("entity", {})
        if not payload_entity:
            payload_entity = payload_data.get("entity", {})

        tx_id = (
            payload_entity.get("notes", {}).get("transaction_id")
            or payload_entity.get("receipt")
            or payload_entity.get("description")
            or ""
        ).strip()

        mer_id = (
            payload_entity.get("notes", {}).get("merchant_id")
            or payload_entity.get("merchant_id")
            or ""
        ).strip()

        if not tx_id:
            return WebhookProcessingResult(
                success=False,
                event_id=eff_event_id,
                transaction_id=None,
                state=None,
                is_duplicate=False,
                rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                rejection_detail="Webhook payload missing correlated internal transaction_id.",
            )

        # Control 4: Atomic Event Registration & Replay Check
        evt_model, is_duplicate = await uow.webhooks.register_event(
            event_id=eff_event_id,
            event_type=event_type,
            transaction_id=tx_id,
            merchant_id=mer_id or "mer_default",
            payload_hash=payload_hash,
        )

        if is_duplicate:
            return WebhookProcessingResult(
                success=True,
                event_id=eff_event_id,
                transaction_id=tx_id,
                state=None,
                is_duplicate=True,
                rejection_reason=None,
                rejection_detail="Duplicate webhook event identity safely deduplicated.",
            )

        # Control 5: Transaction & Merchant Context Binding Check
        db_tx = await uow.transactions.get_transaction(tx_id)
        if db_tx is None:
            return WebhookProcessingResult(
                success=False,
                event_id=eff_event_id,
                transaction_id=tx_id,
                state=None,
                is_duplicate=False,
                rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                rejection_detail=f"Transaction '{tx_id}' not found in persistence store.",
            )

        if mer_id and db_tx.merchant_id != mer_id:
            return WebhookProcessingResult(
                success=False,
                event_id=eff_event_id,
                transaction_id=tx_id,
                state=None,
                is_duplicate=False,
                rejection_reason=RejectionReason.MERCHANT_MISMATCH,
                rejection_detail=(
                    f"Merchant context mismatch: webhook merchant '{mer_id}' "
                    f"!= transaction merchant '{db_tx.merchant_id}'."
                ),
            )

        # Mandate Terminal Check
        man_model = await uow.mandates.get_mandate(db_tx.mandate_id)
        if man_model is not None and man_model.status == MandateStatus.REVOKED.value:
            return WebhookProcessingResult(
                success=False,
                event_id=eff_event_id,
                transaction_id=tx_id,
                state=TransactionState(db_tx.state),
                is_duplicate=False,
                rejection_reason=RejectionReason.MANDATE_NOT_ACTIVE,
                rejection_detail=f"Mandate '{db_tx.mandate_id}' is REVOKED. Event rejected.",
            )

        # Control 6: State Transition Validation
        current_state = TransactionState(db_tx.state)
        target_state: TransactionState | None = None

        if event_type in ("payment.authorized", "payment.captured", "order.paid"):
            target_state = TransactionState.COMMITTED
        elif event_type in ("payment.failed", "order.failed"):
            target_state = TransactionState.ROLLED_BACK

        if target_state is None:
            return WebhookProcessingResult(
                success=True,
                event_id=eff_event_id,
                transaction_id=tx_id,
                state=current_state,
                is_duplicate=False,
                rejection_reason=None,
                rejection_detail=f"Unhandled event_type '{event_type}' ingested without state change.",
            )

        # Terminal state protection: COMMITTED and ROLLED_BACK cannot be overwritten
        if current_state.is_terminal() or current_state in (
            TransactionState.COMMITTED,
            TransactionState.ROLLED_BACK,
        ):
            if current_state != target_state:
                return WebhookProcessingResult(
                    success=False,
                    event_id=eff_event_id,
                    transaction_id=tx_id,
                    state=current_state,
                    is_duplicate=False,
                    rejection_reason=RejectionReason.INVALID_TRANSACTION_STATE,
                    rejection_detail=(
                        f"Terminal state overwrite blocked: transaction is in '{current_state.value}', "
                        f"cannot transition to '{target_state.value}'."
                    ),
                )
            return WebhookProcessingResult(
                success=True,
                event_id=eff_event_id,
                transaction_id=tx_id,
                state=current_state,
                is_duplicate=False,
                rejection_reason=None,
                rejection_detail="Transaction already in target terminal state.",
            )

        # Apply State Transition
        await uow.transactions.transition_transaction_state(tx_id, target_state)

        # Audit Event Log
        await uow.audit.append_event(
            event_id=f"evt_wh_{eff_event_id[:16]}",
            event_type=(
                AuditEventType.PAYMENT_SUCCESS.value
                if target_state is TransactionState.COMMITTED
                else AuditEventType.PAYMENT_FAILED.value
            ),
            transaction_id=tx_id,
            mandate_id=db_tx.mandate_id,
            merchant_id=db_tx.merchant_id,
            buyer_id=db_tx.buyer_id,
            payload={
                "webhook_event_id": eff_event_id,
                "event_type": event_type,
                "target_state": target_state.value,
            },
        )

        return WebhookProcessingResult(
            success=True,
            event_id=eff_event_id,
            transaction_id=tx_id,
            state=target_state,
            is_duplicate=False,
            rejection_reason=None,
            rejection_detail=f"Successfully processed webhook event {eff_event_id}.",
        )
