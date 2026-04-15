from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.trigger import Trigger
from models.user import User
from schemas.event import Event
from core.logger import get_logger
from services.email_service import queue_alert_email

log = get_logger(__name__)

COOLDOWN_MINUTES = 5


def _topic_candidates(event_topic: str) -> set[str]:
    """Return event topic and dot-prefix candidates for trigger matching."""
    candidates = {event_topic}
    parts = event_topic.split(".")
    for i in range(len(parts) - 1, 0, -1):
        candidates.add(".".join(parts[:i]))
    return candidates

def _is_triggered(trigger: Trigger, event: Event) -> bool:
    if trigger.threshold_direction == "above":
        return event.value > trigger.threshold_value
    if trigger.threshold_direction == "below":
        return event.value < trigger.threshold_value
    return False


async def process_event_alerts(db: AsyncSession, manager, event: Event, *, auto_commit: bool = True) -> None:
    topic_candidates = _topic_candidates(event.topic)
    result = await db.execute(
        select(Trigger).where(
            Trigger.topic.in_(topic_candidates),
            Trigger.is_active.is_(True),
        )
    )
    triggers = result.scalars().all()
    now = datetime.now(timezone.utc)
    touched = False

    for trigger in triggers:
        if trigger.expires_at and trigger.expires_at < now:
            continue
        if trigger.current_alert_count >= trigger.notification_count:
            continue
        if not _is_triggered(trigger, event):
            continue

        cooldown = trigger.cooldown_minutes if trigger.cooldown_minutes is not None else COOLDOWN_MINUTES
        if trigger.last_alert_time and now - trigger.last_alert_time < timedelta(minutes=cooldown):
            log.info("alert_cooldown", user_id=str(trigger.user_id), topic=event.topic)
            continue

        user_id = str(trigger.user_id)
        if manager.is_user_connected(user_id, event.topic):
            log.info("onscreen_alert_ready", user_id=user_id, topic=event.topic)
        else:
            user = await db.get(User, UUID(user_id))
            if user and getattr(user, "email", None) and getattr(user, "email_notifications", True):
                subject = f"WatchTower Alert: {event.topic} {trigger.threshold_direction} {trigger.threshold_value}"
                body = (
                    f"Trigger fired for {event.topic}.\n"
                    f"Current value: {event.value} {event.unit}\n"
                    f"Condition: {trigger.threshold_direction} {trigger.threshold_value}\n"
                    f"Timestamp: {event.timestamp.isoformat()}\n"
                )
                await queue_alert_email(
                    db=db,
                    user_id=trigger.user_id,
                    to_email=user.email,
                    subject=subject,
                    body=body,
                )
                log.info("email_alert_queued", user_id=user_id, topic=event.topic)

        trigger.last_alert_time = now
        trigger.current_alert_count += 1
        touched = True

    if touched and auto_commit:
        await db.commit()