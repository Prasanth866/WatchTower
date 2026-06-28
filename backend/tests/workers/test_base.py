from datetime import datetime, timedelta, timezone

import pytest

from core.worker_status import WorkerStatusRegistry
from workers.base import AbstractWorker


class _DummyManager:
    async def publish(self, *_args, **_kwargs):
        return None


class _DummyWorker(AbstractWorker):
    async def fetch(self):
        return None


def test_trip_circuit_marks_worker_degraded_with_details() -> None:
    registry = WorkerStatusRegistry()
    worker = _DummyWorker(_DummyManager(), topic="crypto:btc", status_registry=registry)

    worker._trip_circuit("provider unavailable")

    snapshot = registry.snapshot()
    worker_state = snapshot["workers"]["crypto:btc"]
    assert worker.circuit_state == "open"
    assert worker_state["status"] == "degraded"
    assert worker_state["message"] == "circuit_open"
    assert worker_state["details"]["circuit_state"] == "open"
    assert worker_state["details"]["open_until"] is not None


@pytest.mark.asyncio
async def test_wait_for_open_circuit_transitions_to_half_open_after_timeout() -> None:
    worker = _DummyWorker(_DummyManager(), topic="crypto:btc")
    worker.circuit_state = "open"
    worker._circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)

    should_skip = await worker._wait_for_circuit_if_open()

    assert should_skip is False
    assert worker.circuit_state == "half_open"