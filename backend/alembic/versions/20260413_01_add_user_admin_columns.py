"""add user admin and email notification columns

Revision ID: 20260413_01
Revises: 20260413_00
Create Date: 2026-04-13
"""

from alembic import op


revision = "20260413_01"
down_revision = "20260413_00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"
    )
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications BOOLEAN NOT NULL DEFAULT TRUE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS email_notifications")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_admin")
