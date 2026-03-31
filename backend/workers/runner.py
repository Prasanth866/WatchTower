import asyncio
from workers.crypto import CryptoWorker

async def start_all_workers(manager):
    workers = [
        CryptoWorker(manager,topic="crypto",interval=10)
    ]
    tasks = [asyncio.create_task(worker.run()) for worker in workers]
    await asyncio.gather(*tasks)