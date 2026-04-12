"""API endpoints for managing and retrieving information about topics."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_current_user, get_db
from core.topics import AVAILABLE_TOPICS, TopicInfo
from models.event_log import EventLog
from models.user import User
from schemas.event import EventLog

router = APIRouter()

@router.get("/", response_model=list[TopicInfo])
async def list_topics():
    """Endpoint to retrieve a list of all available topics."""
    return AVAILABLE_TOPICS


@router.get("/{topic}/history",response_model=list[EventLog])
async def get_topic_history(
    topic: str,
    limit: int = Query(default=60, ge=1, le=5760),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return recent event history for a topic, ordered oldest to newest."""
    _ = current_user
    result = await db.execute(
        select(EventLog)
        .where(EventLog.topic == topic)
        .order_by(EventLog.timestamp.desc())
        .limit(limit)
    )
    events = list(reversed(result.scalars().all()))
    return [
        EventLog(
            id=str(event.id),
            topic=event.topic,
            value=event.value,
            unit=event.unit,
            timestamp=event.timestamp,
            metadata=event.metadata_,
        )
        for event in events
    ]
