import uuid
from datetime import datetime,timezone
from sqlalchemy import String ,DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base
from models.trigger import Trigger

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )

    email: Mapped[str] = mapped_column(
        String, 
        unique=True, 
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String, 
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda :datetime.now(timezone.utc)
    )

    subscriptions: Mapped[list["Trigger"]] = relationship(
        "Trigger", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )