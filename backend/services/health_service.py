from sqlalchemy import text
from redis.asyncio import Redis

from core.database import engine


async def get_health_status(redis_client: Redis, worker_status=None, manager=None) -> dict:
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
        # snapshot() is now async — must be awaited
        status["workers"] = await worker_status.snapshot()

    if manager is not None and hasattr(manager, "side_effect_runtime"):
        status["side_effects"] = manager.side_effect_runtime()

    return status
