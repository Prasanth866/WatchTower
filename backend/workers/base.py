import asyncio
from abc import ABC, abstractmethod
from core.worker_status import WorkerStatusRegistry
from schemas.event import Event
from services.broadcaster import ConnectionManager
from core.logger import get_logger

log = get_logger(__name__)

class AbstractWorker(ABC):
    def __init__(
        self,
        manager: ConnectionManager,
        topic: str,
        interval: int = 10,
        max_tries: int = 10,
        status_registry: WorkerStatusRegistry | None = None,
    ):
        self.topic=topic
        self.interval=interval
        self.manager=manager
        self.max_tries=max_tries
        self.failure_count=0
        self.status_registry = status_registry
        if self.status_registry:
            self.status_registry.mark_starting(self.topic, "worker initialized")

    @abstractmethod
    async def fetch(self) -> Event | list[Event]:
        raise NotImplementedError

    async def run(self):
        delay = self.interval
        while True:
            try:
                result = await self.fetch()
                events = result if isinstance(result, list) else [result]
                for event in events:
                    await self.manager.publish(event.topic, event)
                    log.info("Event published", topic=event.topic, value=event.value)
                delay = self.interval
                self.failure_count = 0
                if self.status_registry:
                    self.status_registry.mark_healthy(self.topic)
            except asyncio.CancelledError:
                log.info("Worker cancelled", topic=self.topic)
                if self.status_registry:
                    self.status_registry.mark_stopped(self.topic, "worker cancelled")
                break
            except Exception as e:
                self.failure_count += 1
                error_detail = f"{type(e).__name__}: {str(e)}"
                log.error("Worker error", topic=self.topic, error=error_detail, failure_count=self.failure_count)
                if self.status_registry:
                    self.status_registry.mark_degraded(self.topic, error_detail)
                if self.failure_count >= self.max_tries:
                    log.critical("Max retries reached, stopping worker", topic=self.topic)
                    if self.status_registry:
                        self.status_registry.mark_stopped(self.topic, "max retries reached")
                    break
                delay = min(delay * 2, 300)
            await asyncio.sleep(delay)
    