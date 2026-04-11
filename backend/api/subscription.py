"""API endpoints for managing user subscriptions to topics."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_connection_manager
from models.user import User
from core.dependencies import get_current_user, get_db
from services.broadcaster import ConnectionManager
from services.subscription_service import (
    list_subscriptions_for_user,
    subscribe_user_to_topic,
    unsubscribe_user_from_topic,
)

router = APIRouter()

@router.get("/", response_model=list[str])
async def list_subscriptions(
            db: AsyncSession = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
    """List all topics the current user is subscribed to."""
    return await list_subscriptions_for_user(db, current_user.id)

@router.post("/{topic}", status_code=status.HTTP_201_CREATED)
async def subscribe_to_topic(
            topic: str,
            db: AsyncSession = Depends(get_db),
            current_user: User = Depends(get_current_user)
        ):
    """Subscribe the current user to a topic."""
    await subscribe_user_to_topic(db, current_user.id, topic)
    return {"message": f"Subscribed to {topic}"}

@router.delete("/{topic}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_topic(
            topic: str,
            db: AsyncSession = Depends(get_db),
            current_user: User = Depends(get_current_user),
            manager: ConnectionManager = Depends(get_connection_manager)
        ):
    """Unsubscribe the current user from a topic."""
    await unsubscribe_user_from_topic(db, current_user.id, topic)
    await manager.disconnect_user_from_topic(str(current_user.id), topic)
