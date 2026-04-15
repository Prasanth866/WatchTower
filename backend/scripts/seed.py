import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from core.database import async_session
from core.security import get_password_hash
from core.topics import AVAILABLE_TOPICS
from models.topic_subscription import TopicSubscription
from models.trigger import Trigger
from models.user import User


async def seed() -> None:
    async with async_session() as db:
        email = "test@watchtower.dev"
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                password_hash=get_password_hash("testpass123A!"),
                is_admin=False,
            )
            db.add(user)
            await db.flush()

        for topic_info in AVAILABLE_TOPICS:
            exists = await db.execute(
                select(TopicSubscription).where(
                    TopicSubscription.user_id == user.id,
                    TopicSubscription.topic == topic_info.name,
                )
            )
            if exists.scalar_one_or_none() is None:
                db.add(TopicSubscription(user_id=user.id, topic=topic_info.name))

        trigger_exists = await db.execute(
            select(Trigger).where(
                Trigger.user_id == user.id,
                Trigger.topic == "crypto:btc",
                Trigger.threshold_direction == "above",
            )
        )
        if trigger_exists.scalar_one_or_none() is None:
            db.add(
                Trigger(
                    user_id=user.id,
                    topic="crypto:btc",
                    threshold_value=100000.0,
                    threshold_direction="above",
                    cooldown_minutes=60,
                    notification_count=3,
                    is_active=True,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                )
            )

        await db.commit()
        print("Seed completed: test@watchtower.dev / testpass123A!")


if __name__ == "__main__":
    asyncio.run(seed())