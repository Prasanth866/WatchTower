"""rename topic slugs from crypto:symbol to plain symbol

Revision ID: 20260628_04
Revises: 20260628_03
Create Date: 2026-06-28
"""

from alembic import op

revision = "20260628_04"
down_revision = "20260628_03"
branch_labels = None
depends_on = None

# Map old crypto:xxx slugs to new plain symbols
_SLUG_MAP = {
    "crypto:btc":  "btc",
    "crypto:eth":  "eth",
    "crypto:sol":  "sol",
    "crypto:ada":  "ada",
    "crypto:xrp":  "xrp",
    "crypto:doge": "doge",
    "crypto:dot":  "dot",
}


def upgrade() -> None:
    for old, new in _SLUG_MAP.items():
        op.execute(
            f"UPDATE topic_subscriptions SET topic = '{new}' WHERE topic = '{old}'"
        )
        op.execute(
            f"UPDATE triggers SET topic = '{new}' WHERE topic = '{old}'"
        )


def downgrade() -> None:
    for old, new in _SLUG_MAP.items():
        op.execute(
            f"UPDATE topic_subscriptions SET topic = '{old}' WHERE topic = '{new}'"
        )
        op.execute(
            f"UPDATE triggers SET topic = '{old}' WHERE topic = '{new}'"
        )
