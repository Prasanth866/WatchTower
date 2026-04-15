"""create initial tables

Revision ID: 20260413_00
Revises:
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260413_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_logs_timestamp"), "event_logs", ["timestamp"], unique=False)
    op.create_index(op.f("ix_event_logs_topic"), "event_logs", ["topic"], unique=False)

    op.create_table(
        "password_resets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(op.f("ix_password_resets_token"), "password_resets", ["token"], unique=True)
    op.create_index(op.f("ix_password_resets_user_id"), "password_resets", ["user_id"], unique=False)

    op.create_table(
        "email_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_email", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_queue_sent"), "email_queue", ["sent"], unique=False)
    op.create_index(op.f("ix_email_queue_user_id"), "email_queue", ["user_id"], unique=False)

    op.create_table(
        "topic_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic", name="uq_user_topic"),
    )
    op.create_index(op.f("ix_topic_subscriptions_user_id"), "topic_subscriptions", ["user_id"], unique=False)

    op.create_table(
        "triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("threshold_value", sa.Float(), nullable=False),
        sa.Column("threshold_direction", sa.String(length=10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("notification_count", sa.Integer(), nullable=False),
        sa.Column("current_alert_count", sa.Integer(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("last_alert_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_triggers_user_id"), "triggers", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_triggers_user_id"), table_name="triggers")
    op.drop_table("triggers")

    op.drop_index(op.f("ix_topic_subscriptions_user_id"), table_name="topic_subscriptions")
    op.drop_table("topic_subscriptions")

    op.drop_index(op.f("ix_email_queue_user_id"), table_name="email_queue")
    op.drop_index(op.f("ix_email_queue_sent"), table_name="email_queue")
    op.drop_table("email_queue")

    op.drop_index(op.f("ix_password_resets_user_id"), table_name="password_resets")
    op.drop_index(op.f("ix_password_resets_token"), table_name="password_resets")
    op.drop_table("password_resets")

    op.drop_index(op.f("ix_event_logs_topic"), table_name="event_logs")
    op.drop_index(op.f("ix_event_logs_timestamp"), table_name="event_logs")
    op.drop_table("event_logs")

    op.drop_table("users")
