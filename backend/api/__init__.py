from fastapi import APIRouter
from . import trigger_router, coins_router, auth, health, websocket, paper_trading_router

api_router = APIRouter()

api_router.include_router(health.router, prefix='/health', tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["credentials"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
api_router.include_router(coins_router.router, prefix="/coins", tags=["coins"])
api_router.include_router(trigger_router.router, prefix="/triggers", tags=["triggers"])
api_router.include_router(paper_trading_router.router, prefix="/paper-trading", tags=["paper-trading"])