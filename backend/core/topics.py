"""This module defines the available topics for the WebSocket server, along with their metadata."""
from pydantic import BaseModel


class TopicInfo(BaseModel):
    """Represents metadata about a topic that clients can subscribe to."""
    name: str
    description: str | None = None
    unit: str
    interval_seconds: int


AVAILABLE_TOPICS: list[TopicInfo] = [
    TopicInfo(name="crypto:btc", description="Live Bitcoin prices", unit="USD", interval_seconds=15),
    TopicInfo(name="crypto:eth", description="Live Ethereum prices", unit="USD", interval_seconds=15),
    TopicInfo(name="crypto:sol", description="Live Solana prices", unit="USD", interval_seconds=15),
    TopicInfo(name="crypto:ada", description="Live Cardano prices", unit="USD", interval_seconds=15),
    TopicInfo(name="crypto:xrp", description="Live Ripple prices", unit="USD", interval_seconds=15),
    TopicInfo(name="crypto:doge", description="Live Dogecoin prices", unit="USD", interval_seconds=15),
    TopicInfo(name="crypto:dot", description="Live Polkadot prices", unit="USD", interval_seconds=15),
]

VALID_TOPICS = {topic_info.name for topic_info in AVAILABLE_TOPICS}