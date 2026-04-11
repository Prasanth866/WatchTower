from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.exception import NotFoundException, UnauthorizedException
from models.trigger import Trigger
from schemas.trigger import TriggerCreate, TriggerUpdate

async def list_triggers_for_user(db: AsyncSession, user_id: UUID) -> list[Trigger]:
    query = select(Trigger).where(Trigger.user_id == user_id)
    result = await db.execute(query)
    return list(result.scalars().all())

async def create_trigger(db: AsyncSession, user_id: UUID, obj_in: TriggerCreate) -> Trigger:
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
