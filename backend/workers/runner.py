import asyncio
from core.worker_status import WorkerStatusRegistry
from workers.crypto import CryptoWorker
from workers.email_worker import EmailWorker


async def start_all_workers(manager, status_registry: WorkerStatusRegistry | None = None):
    workers = [
        CryptoWorker(
            manager,
            interval=15,
            status_registry=status_registry,
        ),
        EmailWorker(interval=30, status_registry=status_registry),
    ]
    tasks = [asyncio.create_task(worker.run()) for worker in workers]
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        close_tasks = [worker.client.aclose() for worker in workers if hasattr(worker, 'client')]
        await asyncio.gather(*close_tasks, return_exceptions=True)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)