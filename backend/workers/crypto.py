import httpx
from schemas.event import Event
from workers.base import AbstractWorker
from services.broadcaster import ConnectionManager
from core.config import get_settings
class CryptoWorker(AbstractWorker):
    def __init__(self,manager:ConnectionManager,topic:str,interval:int=10):
        self.api_key = get_settings().CRYPTOCOMPARE_API_KEY
        self.url = "https://min-api.cryptocompare.com/data/price"
        super().__init__(manager,topic,interval)
    async def fetch(self)->Event:
        params = {
            "fsym": "BTC",
            "tsyms": "USD"
        }
        headers = {
            "authorization": f"Apikey {self.api_key}"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.url,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            price = response.json().get("USD")
            return Event(topic=self.topic,
                         value=price,
                         unit='USD',
                         metadata={"coin":"bitcoin"}
            )   