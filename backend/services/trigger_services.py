from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.trigger import Trigger

async def list_triggers_for_user(db: AsyncSession, user_id: UUID) -> list[Trigger]:
    pass

async def create_trigger(db: AsyncSession, user_id: UUID, topic: str, threshold_value: float, threshold_direction: str) -> Trigger:
    pass

async def update_trigger(db: AsyncSession, trigger_id: UUID, user_id: UUID, topic: str | None = None, threshold_value: float | None = None, threshold_direction: str | None = None) -> Trigger:
    pass

async def delete_trigger(db: AsyncSession, trigger_id: UUID, user_id: UUID) -> bool:
    pass