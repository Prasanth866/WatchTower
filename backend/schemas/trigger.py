
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class TriggerBase(BaseModel):
    topic: str = Field(...,max_length=100 ,description="The topic to monitor for triggering alerts")
    threshold_value: float = Field(..., description="The value threshold that will trigger an alert when crossed")
    threshold_direction: str = Field(
        ...,
        pattern="^(above|below)$",
        description="The direction of the threshold comparison: 'above' or 'below'",
        examples=['above']
    )
    is_active: bool = Field(default=True,description="Indicates whether the trigger is active")

class TriggerCreate(TriggerBase):

    expires_at: Optional[datetime] = None
    cooldown_minutes: int = Field(60, ge=0, description="The cooldown period in minutes before another notification can be sent")
    notification_count: int = Field(5, ge=1, le=5, description="Maximum number of notifications to send per trigger activation (1-5)")

class TriggerUpdate(BaseModel):

    topic: Optional[str] = Field(None, max_length=100)
    threshold_value: Optional[float] = None
    threshold_direction: Optional[str] = Field(None, pattern="^(above|below)$")
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    cooldown_minutes: Optional[int] = Field(None, ge=0)
    notification_count: Optional[int] = Field(None, ge=1, le=5)

class TriggerRead(TriggerBase):

    id: UUID
    user_id: UUID
    last_alert_time: Optional[datetime] = None
    current_alert_count: int = 0
    cooldown_minutes: int
    notification_count: int
    created_at : datetime
    
    model_config = ConfigDict(from_attributes=True)
