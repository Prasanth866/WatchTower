from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, timezone
from typing import Any

class Event(BaseModel):
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