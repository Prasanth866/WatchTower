"""Health Check API Endpoint"""
from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from api.dependencies import get_redis_client
from services.health_service import get_health_status

router = APIRouter()

@router.get("")
async def health_check(request: Request, redis_client: Redis = Depends(get_redis_client)):
    """Endpoint to check the health status of the application and its dependencies."""
    worker_status = getattr(request.app.state, "worker_status", None)
    return await get_health_status(redis_client, worker_status)
