"""WebSocket endpoint for real-time price updates on a specific coin."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.dependencies import get_ws_connection_manager
from core.exception import WebSocketAuthenticationError
from services.broadcaster import ConnectionManager
from services.websocket_service import authenticate_websocket_user

router = APIRouter()


@router.websocket("/{coin}")
async def websocket_endpoint(
    websocket: WebSocket,
    coin: str,
    manager: ConnectionManager = Depends(get_ws_connection_manager),
):
    """WebSocket endpoint for clients to receive real-time price updates for a coin."""
    await websocket.accept()

    try:
        user_id = await authenticate_websocket_user(websocket)
    except WebSocketAuthenticationError:
        return

    await manager.subscribe(websocket, coin, user_id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect_socket(websocket, coin)
