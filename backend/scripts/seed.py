import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from typing import cast, Any
from uuid import UUID
from core.database import async_session
from core.security import get_password_hash
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
            )
            db.add(user)
            await db.flush()

        trigger_exists = await db.execute(
            select(Trigger).where(
                Trigger.user_id == user.id,
                Trigger.topic == "btc",
                Trigger.threshold_direction == "above",
            )
        )
        if trigger_exists.scalar_one_or_none() is None:
            db.add(
                Trigger(
                    user_id=cast(UUID, cast(Any, user.id)),
                    topic="btc",
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