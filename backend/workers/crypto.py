from datetime import datetime, timezone
import httpx
from schemas.event import Event
from workers.base import AbstractWorker
from services.broadcaster import ConnectionManager
class CryptoWorker(AbstractWorker):
    def __init__(self,manager:ConnectionManager,topic:str,interval:int=15):
        super().__init__(manager,topic,interval)
        self.url = "https://api.kucoin.com/api/v1/market/orderbook/level1"
        headers = {"User-Agent": "CryptoTracker/1.0 (FastAPI Worker)"}
        self.client = httpx.AsyncClient(
            timeout=15, 
            headers=headers, 
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=3)
        )
    
    async def fetch(self)->Event:
        params = {
            "symbol":"BTC-USDT"
        }
        try:
            response = await self.client.get(
                self.url,
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.ConnectError as e:
            raise Exception("Critical: Persistent DNS or Network Connection Failure")
        except httpx.HTTPError as e:
            raise Exception(f"Network error: {type(e).__name__} - {str(e)}")
        price = data.get('data', {}).get('price')
        if price is None:
            raise ValueError("Could not parse price from KuCoin response")
        return Event(topic=self.topic,
                    value=float(price),
                    unit='USDT',
                    metadata={
                        "coin":"bitcoin",
                        "source":"kucoin",
                        "timestamp":datetime.now(timezone.utc).isoformat()
                    }
                )
    async def close(self):
        await self.client.aclose()