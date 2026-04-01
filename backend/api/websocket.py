import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
from core.security import decode_access_token
router = APIRouter()

@router.websocket("/{topic}")
async def websocket_endpoint(websocket: WebSocket, topic: str):
    await websocket.accept()

    try:
        data = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        token = data.get("token")
        if not token:
            raise ValueError("Token missing")
        user_data = decode_access_token(token)
        user_id = user_data["sub"] if user_data else None
        if not user_id:
            raise ValueError("User ID missing in token")
    except (Exception,asyncio.TimeoutError) as e:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    manager = websocket.app.state.manager
    await manager.subscribe(websocket, topic, user_id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_socket(websocket, topic)