import asyncio
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from core.worker_status import WorkerStatusRegistry
from core.config import get_settings
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
        settings = get_settings()
        self.circuit_failure_threshold = max(1, int(settings.WORKER_CIRCUIT_FAILURE_THRESHOLD))
        self.circuit_open_seconds = max(5, int(settings.WORKER_CIRCUIT_OPEN_SECONDS))
        self.max_backoff_seconds = max(5, int(settings.WORKER_MAX_BACKOFF_SECONDS))
        self.circuit_state = "closed"
        self._circuit_open_until: datetime | None = None
        self.status_registry = status_registry

    async def _on_init(self) -> None:
        """Called once at the start of run() to perform async initialisation."""
        if self.status_registry:
            await self.status_registry.mark_starting(
                self.topic,
                "worker initialized",
                details={"circuit_state": self.circuit_state},
            )

    @abstractmethod
    async def fetch(self) -> Event | list[Event]:
        raise NotImplementedError

    def _trip_circuit(self, reason: str) -> None:
        self.circuit_state = "open"
        self._circuit_open_until = datetime.now(timezone.utc) + timedelta(seconds=self.circuit_open_seconds)
        log.error("Worker circuit opened", topic=self.topic, reason=reason, open_seconds=self.circuit_open_seconds)

    def _close_circuit(self) -> None:
        self.circuit_state = "closed"
        self._circuit_open_until = None

    async def _wait_for_circuit_if_open(self) -> bool:
        if self.circuit_state != "open" or self._circuit_open_until is None:
            return False
        now = datetime.now(timezone.utc)
        if now < self._circuit_open_until:
            remaining_seconds = (self._circuit_open_until - now).total_seconds()
            sleep_for = min(self.interval, max(1.0, remaining_seconds))
            await asyncio.sleep(sleep_for)
            return True

        self.circuit_state = "half_open"
        if self.status_registry:
            await self.status_registry.mark_degraded(
                self.topic,
                "circuit_half_open",
                details={"circuit_state": self.circuit_state},
            )
        return False

    def _next_backoff_delay(self, delay: float) -> float:
        base_delay = min(delay * 2, float(self.max_backoff_seconds))
        jitter = random.uniform(0.8, 1.2)
        return max(float(self.interval), base_delay * jitter)

    async def run(self):
        await self._on_init()
        delay = self.interval
        while True:
            try:
                if await self._wait_for_circuit_if_open():
                    continue

                result = await self.fetch()
                events = result if isinstance(result, list) else [result]
                for event in events:
                    await self.manager.publish(event.topic, event)
                    log.info("Event published", topic=event.topic, value=event.value)
                if self.circuit_state in {"open", "half_open"}:
                    log.info("Worker circuit closed", topic=self.topic)
                self._close_circuit()
                delay = self.interval
                self.failure_count = 0
                if self.status_registry:
                    await self.status_registry.mark_healthy(
                        self.topic,
                        details={"circuit_state": self.circuit_state},
                    )
            except asyncio.CancelledError:
                log.info("Worker cancelled", topic=self.topic)
                if self.status_registry:
                    await self.status_registry.mark_stopped(
                        self.topic,
                        "worker cancelled",
                        details={"circuit_state": self.circuit_state},
                    )
                break
            except Exception as e:
                self.failure_count += 1
                error_detail = f"{type(e).__name__}: {str(e)}"
                log.error("Worker error", topic=self.topic, error=error_detail, failure_count=self.failure_count)
                if self.status_registry:
                    await self.status_registry.mark_degraded(
                        self.topic,
                        error_detail,
                        details={
                            "circuit_state": self.circuit_state,
                            "failure_count": self.failure_count,
                        },
                    )
                if self.failure_count >= self.max_tries:
                    log.critical("Max retries reached, stopping worker", topic=self.topic)
                    if self.status_registry:
                        await self.status_registry.mark_stopped(
                            self.topic,
                            "max retries reached",
                            details={"circuit_state": self.circuit_state},
                        )
                    break
                if self.failure_count >= self.circuit_failure_threshold:
                    self._trip_circuit(error_detail)
                    if self.status_registry:
                        await self.status_registry.mark_degraded(
                            self.topic,
                            "circuit_open",
                            details={
                                "circuit_state": self.circuit_state,
                                "open_until": self._circuit_open_until.isoformat() if self._circuit_open_until else None,
                            },
                        )
                    delay = self.interval
                    continue
                delay = self._next_backoff_delay(delay)
            await asyncio.sleep(delay)