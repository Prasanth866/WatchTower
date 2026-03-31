from fastapi import APIRouter
from services.broadcaster import REDIS_URL
import redis.asyncio as aioredis
from services.database import engine
from sqlalchemy import text
router = APIRouter()
@router.get("")
async def health_check():
    status = {"api": "ok"}
    
    try:
        r = aioredis.from_url(REDIS_URL,decode_responses=True)  
        await r.ping()                             # type: ignore
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