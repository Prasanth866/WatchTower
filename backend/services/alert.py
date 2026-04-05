from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.subscription import Subscription
from schemas.event import Event
import structlog

log = structlog.get_logger()

COOLDOWN_MINUTES = 5

async def evaulate(user_id:str ,websocket:WebSocket, event:Event, db:AsyncSession):
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id, 
            Subscription.topic == event.topic,
            Subscription.is_active==True,
            Subscription.threshold_value != None,
            )
    )
    subscriptions = result.scalars().all()
    for sub in subscriptions:
        triggered = (
            sub.threshold_direction == "above" and event.value > sub.threshold_value
            ) or (
            sub.threshold_direction == "below" and event.value < sub.threshold_value
        )
        if not triggered:
            continue
        now = datetime.now(timezone.utc)
        if sub.last_alert_time and now - sub.last_alert_time < timedelta(minutes=COOLDOWN_MINUTES):
            log.info("alert_cooldown",user_id=user_id,topic=event.topic)
            continue
        await websocket.send_json({
            "type": "alert",
            "topic": event.topic,
            "value": event.value,
            "threshold": sub.threshold_value,
            "direction": sub.threshold_direction,
            "message": f"{event.topic} is {sub.threshold_direction} {sub.threshold_value} {event.unit}",
        })
        sub.last_alert_time = now
        await db.commit()
        log.info("alert_triggered",user_id=user_id,topic=event.topic,value=event.value)