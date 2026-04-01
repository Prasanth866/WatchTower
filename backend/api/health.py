from fastapi import APIRouter, Request
import redis.asyncio as aioredis
from services.database import engine
from sqlalchemy import text
router = APIRouter()
@router.get("")
async def health_check(request: Request):
    status = {"api": "ok"}
    
    try:
        redis_client = request.app.state.manager._redis
        await redis_client.ping()
        status["redis"] = "ok"
    except:
        status["redis"] = "error"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        status["postgres"] = "ok"
    except:
        status["postgres"] = "error"

    return status