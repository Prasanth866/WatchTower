
from fastapi import APIRouter, Depends, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from core.dependencies import get_db, get_current_user
from services.trigger_services import (
    create_trigger,
    delete_trigger,
    list_triggers_for_user,
    update_trigger,
)
from schemas.trigger import TriggerCreate, TriggerUpdate, TriggerRead
from models.user import User

router = APIRouter()

@router.get("/", response_model=list[TriggerRead])
async def list_triggers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await list_triggers_for_user(db, current_user.id)


@router.post("/", response_model=TriggerRead, status_code=status.HTTP_201_CREATED)
async def create_new_trigger(
    trigger_data: TriggerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await create_trigger(db, current_user.id, trigger_data)

@router.patch("/{trigger_id}", response_model=TriggerRead)
async def update_existing_trigger(
    trigger_id: UUID,
    trigger_data: TriggerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await update_trigger(db, current_user.id, trigger_id, trigger_data)

@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_trigger(
    trigger_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):  
    await delete_trigger(db, current_user.id, trigger_id)