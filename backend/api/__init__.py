from fastapi import APIRouter
from . import trigger_router, topics_router, auth, health, subscription, websocket, admin

api_router = APIRouter()

api_router.include_router(health.router,prefix='/health', tags=["health"])
api_router.include_router(auth.router, prefix="/auth",tags=["credentials"])
api_router.include_router(websocket.router,prefix="/ws",tags=["websocket"])
api_router.include_router(subscription.router,prefix="/subscriptions",tags=["subscriptions"])
api_router.include_router(topics_router.router,prefix="/topics",tags=["topics"])
api_router.include_router(trigger_router.router,prefix="/triggers",tags=["triggers"])
api_router.include_router(admin.router,prefix="/admin",tags=["admin"])