from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState
from core.security import decode_access_token
router = APIRouter()

@router.websocket("/{topic}")
async def websocket_endpoint(websocket: WebSocket, topic: str):
    await websocket.accept()

    try:
        data = await websocket.receive_json()
        token = data.get("token")
        if not token:
            raise ValueError("Token missing")
        user_id = decode_access_token(token)["sub"] # type: ignore
    except Exception:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    manager = websocket.app.state.manager
    await manager.subscribe(websocket, topic, user_id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_user(websocket, topic)