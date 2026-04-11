from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exception import ConflictException, NotFoundException
from models.topic_subscription import TopicSubscription
# from core.topics import 

async def list_subscriptions_for_user(db: AsyncSession, user_id: UUID) -> list[str]:
    result = await db.execute(
        select(TopicSubscription).where(TopicSubscription.user_id == user_id)
    )
    return [sub.topic for sub in result.scalars().all()]


async def subscribe_user_to_topic(db: AsyncSession, user_id: UUID, topic: str) -> None:

    existing_subscription = await db.execute(
        select(TopicSubscription).where(
            TopicSubscription.user_id == user_id,
            TopicSubscription.topic == topic,
        )
    )
    if existing_subscription.scalar_one_or_none():
        raise ConflictException("Already subscribed to this topic")

    db.add(TopicSubscription(user_id=user_id, topic=topic))
    await db.commit()


async def unsubscribe_user_from_topic(db: AsyncSession, user_id: UUID, topic: str) -> None:
    result = await db.execute(
        select(TopicSubscription).where(
            TopicSubscription.user_id == user_id,
            TopicSubscription.topic == topic,
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        raise NotFoundException("Subscription not found")

    await db.delete(subscription)
    await db.commit()
