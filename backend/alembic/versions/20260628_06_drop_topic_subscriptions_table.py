"""drop topic subscriptions table

Revision ID: 20260628_06
Revises: 20260628_05
Create Date: 2026-06-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260628_06"
down_revision = "20260628_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop index and table
    op.drop_index("ix_topic_subscriptions_user_id", table_name="topic_subscriptions")
    op.drop_table("topic_subscriptions")


def downgrade() -> None:
    op.create_table(
        "topic_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "topic", name="uq_user_topic")
    )
    op.create_index("ix_topic_subscriptions_user_id", "topic_subscriptions", ["user_id"])
