"""Pydantic model for representing an event with topic, value, unit, timestamp, and metadata."""
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_serializer


class Chartpoint(BaseModel):
    """Lighter model for historical data (Postgres -> Frontend Chart)."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    value: float

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("timestamp", when_used="json")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()


class Event(Chartpoint):
    """Pydantic model for representing an event with topic, value, unit, timestamp, and metadata."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    unit: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class EventLog(Event):
    """History model for persisted events where id is sourced from the DB."""
    id: str