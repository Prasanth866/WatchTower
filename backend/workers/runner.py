import asyncio
from workers.crypto import CryptoWorker
from workers.basketball import BasketballWorker


async def start_all_workers(manager):
    workers = [
        CryptoWorker(manager, topic="crypto:btc", interval=15),
        BasketballWorker(manager, topic="basketball:nba", interval=60),
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