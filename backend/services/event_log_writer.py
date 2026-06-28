import asyncio
from sqlalchemy import insert
from core.config import get_settings
from core.database import async_session
from core.logger import get_logger
from models.event_log import EventLog
from schemas.event import Event

log = get_logger(__name__)


class EventLogWriter:
    def __init__(self) -> None:
        settings = get_settings()
        self._batch_size = max(1, int(settings.EVENT_LOG_BATCH_SIZE))
        self._flush_interval = max(0.5, float(settings.EVENT_LOG_FLUSH_INTERVAL_SECONDS))
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max(1, int(settings.EVENT_LOG_QUEUE_MAXSIZE)))
        self._task: asyncio.Task | None = None
        self._stopping = False
        self._dropped_events = 0

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def dropped_events(self) -> int:
        return self._dropped_events

    async def startup(self) -> None:
        self._stopping = False
        self._task = asyncio.create_task(self._run())
        log.info("EventLogWriter started", batch_size=self._batch_size, flush_interval=self._flush_interval)

    async def shutdown(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        await self._flush_remaining()
        log.info("EventLogWriter stopped", queue_size=self.queue_size, dropped_events=self._dropped_events)

    async def enqueue(self, event: Event) -> None:
        if self._stopping:
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self._dropped_events += 1
            log.error("Event log queue full; dropping event", topic=event.topic, dropped_events=self._dropped_events)

    async def _run(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_batch(self._batch_size)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.error("EventLogWriter flush error", error=str(exc))

    async def _flush_remaining(self) -> None:
        while not self._queue.empty():
            await self._flush_batch(self._batch_size)

    async def _flush_batch(self, limit: int) -> None:
        rows = []
        for _ in range(limit):
            try:
                event = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            rows.append(
                {
                    "topic": event.topic,
                    "value": event.value,
                    "unit": event.unit,
                    "timestamp": event.timestamp,
                    "metadata_": event.metadata,
                }
            )

        if not rows:
            return

        async with async_session() as db:
            await db.execute(insert(EventLog), rows)
            await db.commit()

        log.debug("Event log batch flushed", batch_size=len(rows), queue_size=self.queue_size)
