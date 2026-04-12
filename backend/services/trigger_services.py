from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.exception import BadRequestException, NotFoundException, UnauthorizedException
from core.topics import VALID_TOPICS
from models.trigger import Trigger
from schemas.trigger import TriggerCreate, TriggerUpdate


def _validate_trigger_topic(topic: str) -> None:
    if topic not in VALID_TOPICS:
        raise BadRequestException(f"Invalid trigger topic '{topic}'")


def _validate_expires_at(expires_at: datetime | None) -> None:
    if expires_at is None:
        return

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise BadRequestException("expires_at must be in the future")

async def list_triggers_for_user(db: AsyncSession, user_id: UUID) -> list[Trigger]:
    query = select(Trigger).where(Trigger.user_id == user_id)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_trigger(db: AsyncSession, user_id: UUID, obj_in: TriggerCreate) -> Trigger:
    _validate_trigger_topic(obj_in.topic)
    _validate_expires_at(obj_in.expires_at)

    db_obj = Trigger(
        **obj_in.model_dump(),
        user_id = user_id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_trigger(db: AsyncSession, user_id: UUID, trigger_id: UUID, obj_in: TriggerUpdate) -> Trigger:
    query = select(Trigger).where(Trigger.id == trigger_id)
    result = await db.execute(query)
    db_obj = result.scalar_one_or_none()
    if not db_obj:
        raise NotFoundException("Trigger not found")
    if db_obj.user_id != user_id:
        raise UnauthorizedException("Unauthorized")
    update_data = obj_in.model_dump(exclude_unset=True)
    if "topic" in update_data and update_data["topic"] is not None:
        _validate_trigger_topic(update_data["topic"])
    if "expires_at" in update_data:
        _validate_expires_at(update_data["expires_at"])
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_trigger(db: AsyncSession, user_id: UUID, trigger_id: UUID) -> None:
    result = await db.execute(select(Trigger).where(Trigger.id == trigger_id))
    db_obj = result.scalar_one_or_none()
    if db_obj is None:
        raise NotFoundException("Trigger not found")
    if db_obj.user_id != user_id:
        raise UnauthorizedException("Unauthorized")

    await db.delete(db_obj)
    await db.commit()
