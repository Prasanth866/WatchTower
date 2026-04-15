from sqlalchemy import text
from redis.asyncio import Redis

from core.database import engine


async def get_health_status(redis_client: Redis, worker_status=None) -> dict:
    status = {"api": "ok"}

    try:
        await redis_client.ping()
        status["redis"] = "ok"
    except Exception:
        status["redis"] = "error"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except Exception:
        status["postgres"] = "error"

    if worker_status is not None:
        status["workers"] = worker_status.snapshot()

    return status
