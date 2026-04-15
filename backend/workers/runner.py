import asyncio
from core.worker_status import WorkerStatusRegistry
from workers.crypto import CryptoWorker
from workers.basketball import BasketballWorker
from workers.email_worker import EmailWorker


async def start_all_workers(manager, status_registry: WorkerStatusRegistry | None = None):
    workers = [
        CryptoWorker(
            manager,
            topic="crypto:btc",
            interval=15,
            symbol="BTC-USDT",
            coin_name="bitcoin",
            status_registry=status_registry,
        ),
        CryptoWorker(
            manager,
            topic="crypto:ethereum",
            interval=15,
            symbol="ETH-USDT",
            coin_name="ethereum",
            status_registry=status_registry,
        ),
        BasketballWorker(manager, topic="basketball:nba", interval=60, status_registry=status_registry),
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