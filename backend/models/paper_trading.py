"""SQLAlchemy models for paper trading balances, holdings, and transactions."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class PaperAccount(Base):
    """Represents a virtual paper trading account for a user."""
    __tablename__ = "paper_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    cash_balance: Mapped[float] = mapped_column(
        Float,
        default=100000.0,
        nullable=False
    )
    initial_balance: Mapped[float] = mapped_column(
        Float,
        default=100000.0,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    holdings: Mapped[list["Holding"]] = relationship(
        "Holding",
        back_populates="account",
        cascade="all, delete-orphan"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="account",
        cascade="all, delete-orphan"
    )


class Holding(Base):
    """Represents the current ownership quantities of a coin in an account."""
    __tablename__ = "holdings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    coin_symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )
    quantity: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )
    average_buy_price: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    account: Mapped["PaperAccount"] = relationship(
        "PaperAccount",
        back_populates="holdings"
    )

    __table_args__ = (
        UniqueConstraint("account_id", "coin_symbol", name="uq_account_coin"),
    )


class Transaction(Base):
    """Represents a executed trade transaction record (BUY/SELL) log."""
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("paper_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    coin_symbol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True
    )
    type: Mapped[str] = mapped_column(
        String,  # BUY or SELL
        nullable=False
    )
    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    price: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    total: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    account: Mapped["PaperAccount"] = relationship(
        "PaperAccount",
        back_populates="transactions"
    )
