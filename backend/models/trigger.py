"""Model representing a user's trigger for a specific topic and threshold."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, String ,Float ,Boolean ,ForeignKey ,Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base
if TYPE_CHECKING:
    from .user import User

class Trigger(Base):
    """Model representing a user's trigger for a specific topic and threshold."""
    __tablename__ = "triggers"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id",ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    threshold_value: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    threshold_direction: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    notification_count: Mapped[int] = mapped_column(
        Integer, 
        default=5, 
        nullable=False
    )
    current_alert_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    cooldown_minutes: Mapped[int] = mapped_column(
        Integer, 
        default=60, 
        nullable=False
    )

    last_alert_time: Mapped[datetime | None] = mapped_column(
                                                    DateTime(timezone=True),
                                                    nullable=True
                                                )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="triggers"
    )