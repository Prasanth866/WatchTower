import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, String ,Float ,Boolean ,ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
if TYPE_CHECKING:
    from .user import User
from core.database import Base

class Trigger(Base):
    __tablename__ = "triggers"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id",ondelete="CASCADE"), 
        nullable=False
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

    user: Mapped["User"] = relationship(
        "User", 
        back_populates="subscriptions"
    )
    last_alert_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True )