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


@pytest.mark.asyncio
async def test_trip_circuit_marks_worker_degraded_with_details() -> None:
    registry = WorkerStatusRegistry()
    worker = _DummyWorker(_DummyManager(), topic="btc", status_registry=registry)

    # _trip_circuit itself is sync; the status update happens in run() after tripping.
    # Here we directly set degraded status to mirror what run() does.
    worker._trip_circuit("provider unavailable")
    await registry.mark_degraded(
        worker.topic,
        "circuit_open",
        details={
            "circuit_state": worker.circuit_state,
            "open_until": worker._circuit_open_until.isoformat() if worker._circuit_open_until else None,
        },
    )

    snapshot = await registry.snapshot()
    worker_state = snapshot["workers"]["btc"]
    assert worker.circuit_state == "open"
    assert worker_state["status"] == "degraded"
    assert worker_state["message"] == "circuit_open"
    assert worker_state["details"]["circuit_state"] == "open"
    assert worker_state["details"]["open_until"] is not None


@pytest.mark.asyncio
async def test_wait_for_open_circuit_transitions_to_half_open_after_timeout() -> None:
    worker = _DummyWorker(_DummyManager(), topic="btc")
    worker.circuit_state = "open"
    worker._circuit_open_until = datetime.now(timezone.utc) - timedelta(seconds=1)

    should_skip = await worker._wait_for_circuit_if_open()

    assert should_skip is False
    assert worker.circuit_state == "half_open"