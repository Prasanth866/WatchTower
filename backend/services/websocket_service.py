import asyncio

from fastapi import WebSocket, status
from fastapi.websockets import WebSocketState

from core.security import decode_access_token


async def authenticate_websocket_user(websocket: WebSocket) -> str:
    try:
        data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        token = data.get("token")
        if not token:
            raise ValueError("Token missing")

        user_data = decode_access_token(token)
        user_id = user_data["sub"] if user_data else None
        if not user_id:
            raise ValueError("User ID missing in token")

        return str(user_id)
    except (Exception, asyncio.TimeoutError):
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise
