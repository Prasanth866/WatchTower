from core.database import async_session
from models.event_log import EventLog
from schemas.event import Event
from services.alert import process_event_alerts


async def process_event_side_effects(manager, event: Event) -> None:
    """Persist event data and trigger alert processing outside websocket push flow."""
    event_log_writer = getattr(manager, "event_log_writer", None)
    if event_log_writer is not None:
        await event_log_writer.enqueue(event)

    async with async_session() as db:
        if event_log_writer is None:
            db.add(
                EventLog(
                    topic=event.topic,
                    value=event.value,
                    unit=event.unit,
                    timestamp=event.timestamp,
                    metadata_=event.metadata,
                )
            )
        await process_event_alerts(db, manager, event, auto_commit=False)
        await db.commit()
