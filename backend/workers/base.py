import asyncio
import structlog
from abc import ABC, abstractmethod
from schemas.event import Event
from services.broadcaster import ConnectionManager

log = structlog.get_logger()

class AbstractWorker(ABC):
    def __init__(self,manager:ConnectionManager,topic:str,interval:int=10,max_tries:int=10):
        self.topic=topic
        self.interval=interval
        self.manager=manager
        self.max_tries=max_tries
        self.failure_count=0

    @abstractmethod
    async def fetch(self)->Event:
        raise NotImplementedError

    async def run(self):
        delay=self.interval
        while True:
            try:
                event=await self.fetch()
                await self.manager.publish(self.topic,event)
                log.info("Event published",topic=self.topic,value=event.value)
                delay=self.interval
                self.failure_count=0
            except asyncio.CancelledError:
                log.info("Worker cancelled",topic=self.topic)
                break
            except Exception as e:
                self.failure_count+=1
                log.error("Worker error",topic=self.topic,error=str(e),failure_count=self.failure_count)
                if self.failure_count >= self.max_tries:
                    log.critical("Max retries reached, stopping worker",topic=self.topic)
                    break
                delay=min(delay*2,300)
            await asyncio.sleep(delay)
    