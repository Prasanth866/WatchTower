from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from api.dependencies import get_redis_client
from services.health_service import get_health_status

router = APIRouter()


@router.get("")
async def health_check(redis_client: Redis = Depends(get_redis_client)):
    return await get_health_status(redis_client)