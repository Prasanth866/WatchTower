from uuid import uuid4, UUID
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from services.database import Base
from datetime import datetime,timezone
class TopicSubscription(Base):
    __tablename__ = "topic_subscriptions"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id",ondelete="CASCADE"), 
        nullable=False,
        index=True
    )

    topic: Mapped[str] = mapped_column(
        String(100), 
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    __table_args__ = (UniqueConstraint('user_id', 'topic', name='uq_user_topic'),)