"""This module contains the dependencies for the API routes."""
from fastapi import Depends, Request, WebSocket
from redis.asyncio import Redis
from services.broadcaster import ConnectionManager

def get_connection_manager(request: Request) -> ConnectionManager:
    """Dependency to get the connection manager from the app state."""
    return request.app.state.manager


def get_ws_connection_manager(websocket: WebSocket) -> ConnectionManager:
    """Dependency to get the WebSocket connection manager from the app state."""
    return websocket.app.state.manager


def get_redis_client(manager: ConnectionManager = Depends(get_connection_manager)) -> Redis:
    """Dependency to get the Redis client from the connection manager."""
    return manager.redis
