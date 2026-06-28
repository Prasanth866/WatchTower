"""add trigger topic active index

Revision ID: 20260628_02
Revises: 20260413_01
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260628_02"
down_revision = "20260413_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_trigger_topic_active", "triggers", ["topic", "is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_trigger_topic_active", table_name="triggers")
