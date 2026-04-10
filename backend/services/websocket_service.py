from fastapi import WebSocket, status
from core.security import decode_access_token
from core.logger import get_logger

log = get_logger(__name__)

async def authenticate_websocket_user(websocket: WebSocket) -> str:
    auth_header = websocket.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise ValueError("Missing or invalid authorization header")

    token = auth_header[len("Bearer "):]
    try:
        user_data = decode_access_token(token)
        user_id = user_data["sub"] if user_data else None
        if not user_id:
            log.error("User ID missing in token", token=token)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise ValueError("User ID missing in token")

        return str(user_id)
    except Exception as e:
        log.error("Authentication failed", token=token, error=str(e))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise