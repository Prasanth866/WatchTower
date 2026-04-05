from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.topic_subscription import TopicSubscription
from models.user import User
from core.dependencies import get_current_user, get_db

router = APIRouter()

@router.get("/", response_model=list[str])
async def list_subscriptions(db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(TopicSubscription).where(TopicSubscription.user_id == current_user.id)
    )
    return [sub.topic for sub in result.scalars().all()]

@router.post("/{topic}", status_code=status.HTTP_201_CREATED)
async def subscribe_to_topic(topic: str, db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    existing_subscription = await db.execute(
        select(TopicSubscription).where(TopicSubscription.user_id == current_user.id, TopicSubscription.topic == topic)
    )
    if existing_subscription.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already subscribed to this topic")
    db.add(TopicSubscription(user_id=current_user.id, topic=topic))
    await db.commit()
    return {"message": f"Subscribed to {topic}"}

@router.delete("/{topic}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_topic(topic: str, request: Request,db: AsyncSession = Depends(get_db),current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(TopicSubscription).where(TopicSubscription.user_id == current_user.id, TopicSubscription.topic == topic)
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    await db.delete(subscription)
    await db.commit()

    manager = request.app.state.manager
    await manager.disconnect_user_from_topic(str(current_user.id), topic)

