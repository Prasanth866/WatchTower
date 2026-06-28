"""create paper trading tables

Revision ID: 20260628_05
Revises: 20260628_04
Create Date: 2026-06-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260628_05"
down_revision = "20260628_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create paper_accounts table
    op.create_table(
        "paper_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cash_balance", sa.Float(), nullable=False),
        sa.Column("initial_balance", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_paper_accounts_user_id"), "paper_accounts", ["user_id"], unique=True)

    # Create holdings table
    op.create_table(
        "holdings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coin_symbol", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("average_buy_price", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "coin_symbol", name="uq_account_coin")
    )
    op.create_index(op.f("ix_holdings_account_id"), "holdings", ["account_id"], unique=False)
    op.create_index(op.f("ix_holdings_coin_symbol"), "holdings", ["coin_symbol"], unique=False)

    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("coin_symbol", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index(op.f("ix_transactions_account_id"), "transactions", ["account_id"], unique=False)
    op.create_index(op.f("ix_transactions_coin_symbol"), "transactions", ["coin_symbol"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_transactions_coin_symbol"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_account_id"), table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_holdings_coin_symbol"), table_name="holdings")
    op.drop_index(op.f("ix_holdings_account_id"), table_name="holdings")
    op.drop_table("holdings")

    op.drop_index(op.f("ix_paper_accounts_user_id"), table_name="paper_accounts")
    op.drop_table("paper_accounts")
