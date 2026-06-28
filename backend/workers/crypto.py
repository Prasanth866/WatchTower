from datetime import datetime, timezone
import httpx
from core.worker_status import WorkerStatusRegistry
from schemas.event import Event
from workers.base import AbstractWorker
from services.broadcaster import ConnectionManager


class CryptoWorker(AbstractWorker):
    def __init__(
        self,
        manager: ConnectionManager,
        interval: int = 15,
        status_registry: WorkerStatusRegistry | None = None,
    ):
        super().__init__(manager, topic="all", interval=interval, status_registry=status_registry)
        self.coin_mapping = {
            "bitcoin":  ("btc",  "USD"),
            "ethereum": ("eth",  "USD"),
            "solana":   ("sol",  "USD"),
            "cardano":  ("ada",  "USD"),
            "ripple":   ("xrp",  "USD"),
            "dogecoin": ("doge", "USD"),
            "polkadot": ("dot",  "USD"),
        }
        self.url = "https://api.coingecko.com/api/v3/simple/price"
        headers = {"User-Agent": "CryptoTracker/1.0 (FastAPI Worker)"}
        self.client = httpx.AsyncClient(
            timeout=15,
            headers=headers,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            # NOTE: transport-level retries are intentionally NOT set here.
            # The AbstractWorker circuit-breaker (base.py) is the authoritative
            # retry boundary.  Adding transport retries on top would multiply
            # actual network attempts by max_tries, cause unexpectedly long
            # delays, and produce misleading failure_count metrics.
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0"),
        )

    async def fetch(self) -> list[Event]:
        coin_ids = ",".join(self.coin_mapping.keys())
        params = {
            "ids": coin_ids,
            "vs_currencies": "usd",
        }
        try:
            response = await self.client.get(self.url, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError:
            raise Exception("Critical: Persistent DNS or Network Connection Failure")
        except httpx.HTTPError as e:
            raise Exception(f"Network error: {type(e).__name__} - {str(e)}")

        events = []
        for coin_id, (topic, unit) in self.coin_mapping.items():
            coin_data = data.get(coin_id)
            if coin_data is None:
                continue
            price = coin_data.get("usd")
            if price is None:
                continue

            events.append(
                Event(
                    topic=topic,
                    value=float(price),
                    unit=unit,
                    metadata={
                        "coin": coin_id,
                        "source": "coingecko",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
        return events

    async def close(self):
        await self.client.aclose()