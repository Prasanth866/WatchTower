from fastapi import Depends, Request, WebSocket
from redis.asyncio import Redis

from services.broadcaster import ConnectionManager


def get_connection_manager(request: Request) -> ConnectionManager:
    return request.app.state.manager


def get_ws_connection_manager(websocket: WebSocket) -> ConnectionManager:
    return websocket.app.state.manager


def get_redis_client(manager: ConnectionManager = Depends(get_connection_manager)) -> Redis:
    return manager.redis
