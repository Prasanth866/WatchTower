"""Pydantic model for representing an event with topic, value, unit, timestamp, and metadata."""
from typing import Any
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

class Event(BaseModel):
    """Pydantic model for representing an event with topic, value, unit, timestamp, and metadata."""
    topic: str
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )

class EventLog(Event):
    """Pydantic model for representing an event log entry, extending the base Event model with an ID."""
    id: str