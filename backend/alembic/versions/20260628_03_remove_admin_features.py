"""remove admin features

Revision ID: 20260628_03
Revises: 20260628_02
Create Date: 2026-06-28
"""

from alembic import op
import sqlalchemy as sa


revision = "20260628_03"
down_revision = "20260628_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "is_admin")


def downgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")))
