from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminUserRead(BaseModel):
    id: UUID
    email: EmailStr
    is_admin: bool
    email_notifications: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserList(BaseModel):
    users: list[AdminUserRead]
    total: int


class AdminStatsRead(BaseModel):
    total_users: int
    total_subscriptions: int
    total_triggers: int
    active_triggers: int
    pending_emails: int


class AdminTopicRead(BaseModel):
    id: UUID
    user_id: UUID
    topic: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminTriggerRead(BaseModel):
    id: UUID
    user_id: UUID
    topic: str
    threshold_value: float
    threshold_direction: str
    is_active: bool
    last_alert_time: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)