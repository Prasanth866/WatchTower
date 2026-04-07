from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from core.dependencies import get_current_user, get_db
from services.subscription_service import (
    list_subscriptions_for_user,
    subscribe_user_to_topic,
    unsubscribe_user_from_topic,
)

router = APIRouter()

@router.get("/", response_model=list[str])
async def list_subscriptions(db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    return await list_subscriptions_for_user(db, current_user.id)

@router.post("/{topic}", status_code=status.HTTP_201_CREATED)
async def subscribe_to_topic(topic: str, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    try:
        await subscribe_user_to_topic(db, current_user.id, topic)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"message": f"Subscribed to {topic}"}

@router.delete("/{topic}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_topic(topic: str, request: Request,db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    removed = await unsubscribe_user_from_topic(db, current_user.id, topic)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")

    manager = request.app.state.manager
    await manager.disconnect_user_from_topic(str(current_user.id), topic)

