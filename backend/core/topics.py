"""This module defines the available topics for the WebSocket server, along with their metadata."""
from pydantic import BaseModel


class TopicInfo(BaseModel):
    """Represents metadata about a topic that clients can subscribe to."""
    name: str
    description: str | None = None
    unit: str
    interval_seconds: int


AVAILABLE_TOPICS: list[TopicInfo] = [
    TopicInfo(name="crypto:btc", description="Live BTC prices", unit="USD", interval_seconds=15),
    TopicInfo(name="basketball:nba", description="Live NBA scores", unit="Points", interval_seconds=60),
]
