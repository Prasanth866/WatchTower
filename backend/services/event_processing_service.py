from core.database import async_session
from schemas.event import Event
from services.alert import process_event_alerts


async def process_event_side_effects(manager, event: Event) -> None:
    """Trigger alert processing outside websocket push flow."""
    async with async_session() as db:
        await process_event_alerts(db, manager, event, auto_commit=False)
        await db.commit()
