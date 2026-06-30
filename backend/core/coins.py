"""Defines the available cryptocurrency coins and their metadata for WebSocket streaming."""
from pydantic import BaseModel


class CoinInfo(BaseModel):
    """Metadata about a coin that clients can subscribe to."""
    symbol: str
    name: str
    description: str | None = None
    unit: str
    interval_seconds: int
    price: float | None = None
    change24h: float | None = None
    marketCap: float | None = None
    totalVolume: float | None = None


AVAILABLE_COINS: list[CoinInfo] = [
    CoinInfo(symbol="btc",  name="Bitcoin",  description="Live Bitcoin price",  unit="USD", interval_seconds=15),
    CoinInfo(symbol="eth",  name="Ethereum", description="Live Ethereum price", unit="USD", interval_seconds=15),
    CoinInfo(symbol="sol",  name="Solana",   description="Live Solana price",   unit="USD", interval_seconds=15),
    CoinInfo(symbol="ada",  name="Cardano",  description="Live Cardano price",  unit="USD", interval_seconds=15),
    CoinInfo(symbol="xrp",  name="Ripple",   description="Live Ripple price",   unit="USD", interval_seconds=15),
    CoinInfo(symbol="doge", name="Dogecoin", description="Live Dogecoin price", unit="USD", interval_seconds=15),
    CoinInfo(symbol="dot",  name="Polkadot", description="Live Polkadot price", unit="USD", interval_seconds=15),
]

VALID_COINS: set[str] = {coin.symbol for coin in AVAILABLE_COINS}
