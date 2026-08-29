"""Initial Mandate Gateway persistence schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-08-28 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Merchants table
    op.create_table(
        "merchants",
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("razorpay_account_id", sa.String(length=64), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("merchant_id"),
    )
    op.create_index(
        op.f("ix_merchants_razorpay_account_id"), "merchants", ["razorpay_account_id"], unique=False
    )

    # 2. Merchant Policies table
    op.create_table(
        "merchant_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("autonomous_limit_paise", sa.BigInteger(), nullable=False),
        sa.Column("step_up_threshold_paise", sa.BigInteger(), nullable=False),
        sa.Column("allowed_categories_json", sa.Text(), nullable=False),
        sa.Column("allowed_operations_json", sa.Text(), nullable=False),
        sa.Column("blocked_operations_json", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "autonomous_limit_paise >= 0", name="chk_policy_autonomous_limit_non_negative"
        ),
        sa.CheckConstraint(
            "step_up_threshold_paise >= 0", name="chk_policy_step_up_threshold_non_negative"
        ),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.merchant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", "policy_version", name="uq_merchant_policy_version"),
    )
    op.create_index(
        op.f("ix_merchant_policies_merchant_id"), "merchant_policies", ["merchant_id"], unique=False
    )

    # 3. Products table
    op.create_table(
        "products",
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_paise", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price_paise >= 0", name="chk_product_price_non_negative"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.merchant_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_index(op.f("ix_products_merchant_id"), "products", ["merchant_id"], unique=False)
    op.create_index(op.f("ix_products_category"), "products", ["category"], unique=False)

    # 4. Mandates table
    op.create_table(
        "mandates",
        sa.Column("mandate_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=True),
        sa.Column("category_scope", sa.String(length=64), nullable=True),
        sa.Column("daily_budget_paise", sa.BigInteger(), nullable=False),
        sa.Column("cumulative_budget_paise", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("region", sa.String(length=32), nullable=False, server_default="IN"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("daily_budget_paise >= 0", name="chk_mandate_daily_budget_non_negative"),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.merchant_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("mandate_id"),
    )
    op.create_index(op.f("ix_mandates_buyer_id"), "mandates", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_mandates_merchant_id"), "mandates", ["merchant_id"], unique=False)
    op.create_index(
        op.f("ix_mandates_category_scope"), "mandates", ["category_scope"], unique=False
    )
    op.create_index(op.f("ix_mandates_status"), "mandates", ["status"], unique=False)
    op.create_index(op.f("ix_mandates_expires_at"), "mandates", ["expires_at"], unique=False)

    # 5. Transactions table
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("buyer_id", sa.String(length=64), nullable=False),
        sa.Column("merchant_id", sa.String(length=64), nullable=False),
        sa.Column("mandate_id", sa.String(length=64), nullable=False),
        sa.Column("cart_hash", sa.String(length=64), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("region", sa.String(length=32), nullable=False, server_default="IN"),
        sa.Column("auth_decision", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=128), nullable=True),
        sa.Column("provider_status", sa.String(length=32), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_paise >= 0", name="chk_transaction_amount_non_negative"),
        sa.ForeignKeyConstraint(["mandate_id"], ["mandates.mandate_id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.merchant_id"]),
        sa.PrimaryKeyConstraint("transaction_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_transaction_idempotency_key"),
    )
    op.create_index(op.f("ix_transactions_buyer_id"), "transactions", ["buyer_id"], unique=False)
    op.create_index(
        op.f("ix_transactions_merchant_id"), "transactions", ["merchant_id"], unique=False
    )
    op.create_index(
        op.f("ix_transactions_mandate_id"), "transactions", ["mandate_id"], unique=False
    )
    op.create_index(op.f("ix_transactions_state"), "transactions", ["state"], unique=False)
    op.create_index(
        op.f("ix_transactions_idempotency_key"), "transactions", ["idempotency_key"], unique=True
    )
    op.create_index(
        op.f("ix_transactions_created_at"), "transactions", ["created_at"], unique=False
    )

    # 6. Budget Reservations table
    op.create_table(
        "budget_reservations",
        sa.Column("reservation_id", sa.String(length=64), nullable=False),
        sa.Column("mandate_id", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("requested_paise", sa.BigInteger(), nullable=False),
        sa.Column("reserved_paise", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("requested_paise >= 0", name="chk_reservation_requested_non_negative"),
        sa.CheckConstraint("reserved_paise >= 0", name="chk_reservation_reserved_non_negative"),
        sa.ForeignKeyConstraint(["mandate_id"], ["mandates.mandate_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.transaction_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("reservation_id"),
        sa.UniqueConstraint(
            "mandate_id", "transaction_id", name="uq_mandate_transaction_reservation"
        ),
    )
    op.create_index(
        op.f("ix_budget_reservations_mandate_id"),
        "budget_reservations",
        ["mandate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_budget_reservations_transaction_id"),
        "budget_reservations",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_budget_reservations_state"), "budget_reservations", ["state"], unique=False
    )

    # 7. Step-Up Challenges table
    op.create_table(
        "step_up_challenges",
        sa.Column("challenge_id", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_classification", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approver_metadata", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.transaction_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("challenge_id"),
    )
    op.create_index(
        op.f("ix_step_up_challenges_transaction_id"),
        "step_up_challenges",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_step_up_challenges_status"), "step_up_challenges", ["status"], unique=False
    )

    # 8. Replay Records table
    op.create_table(
        "replay_records",
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("fingerprint"),
    )
    op.create_index(
        op.f("ix_replay_records_transaction_id"), "replay_records", ["transaction_id"], unique=False
    )
    op.create_index(
        op.f("ix_replay_records_created_at"), "replay_records", ["created_at"], unique=False
    )

    # 9. Nonce Records table
    op.create_table(
        "nonce_records",
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("mandate_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("nonce"),
    )
    op.create_index(
        op.f("ix_nonce_records_transaction_id"), "nonce_records", ["transaction_id"], unique=False
    )

    # 10. Audit Events table
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_number", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=True),
        sa.Column("mandate_id", sa.String(length=64), nullable=True),
        sa.Column("merchant_id", sa.String(length=64), nullable=True),
        sa.Column("buyer_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("event_hash", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("sequence_number", name="uq_audit_sequence_number"),
        sa.UniqueConstraint("event_hash", name="uq_audit_event_hash"),
    )
    op.create_index(
        op.f("ix_audit_events_sequence_number"), "audit_events", ["sequence_number"], unique=True
    )
    op.create_index(
        op.f("ix_audit_events_event_type"), "audit_events", ["event_type"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_transaction_id"), "audit_events", ["transaction_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_mandate_id"), "audit_events", ["mandate_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_merchant_id"), "audit_events", ["merchant_id"], unique=False
    )
    op.create_index(op.f("ix_audit_events_buyer_id"), "audit_events", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_audit_events_timestamp"), "audit_events", ["timestamp"], unique=False)

    # 11. Action Receipts table
    op.create_table(
        "action_receipts",
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("audit_event_id", sa.String(length=64), nullable=False),
        sa.Column("canonical_payload_hash", sa.String(length=64), nullable=False),
        sa.Column("signature_hex", sa.Text(), nullable=False),
        sa.Column("public_key_hex", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_event_id"], ["audit_events.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.transaction_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("receipt_id"),
    )
    op.create_index(
        op.f("ix_action_receipts_transaction_id"),
        "action_receipts",
        ["transaction_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_action_receipts_audit_event_id"),
        "action_receipts",
        ["audit_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("action_receipts")
    op.drop_table("audit_events")
    op.drop_table("nonce_records")
    op.drop_table("replay_records")
    op.drop_table("step_up_challenges")
    op.drop_table("budget_reservations")
    op.drop_table("transactions")
    op.drop_table("mandates")
    op.drop_table("products")
    op.drop_table("merchant_policies")
    op.drop_table("merchants")
