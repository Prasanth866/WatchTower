
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from api.dependencies import get_connection_manager
from core.dependencies import get_db, get_current_user
from services.broadcaster import ConnectionManager
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
    try:
        return await create_trigger(db, current_user.id, trigger_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

@router.patch("/{trigger_id}", response_model=TriggerRead)
async def update_existing_trigger(
    trigger_id: UUID,
    trigger_data: TriggerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return await update_trigger(db, current_user.id, trigger_id, trigger_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_trigger(
    trigger_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    manager: ConnectionManager = Depends(get_connection_manager)
):
    removed = await delete_trigger(db, current_user.id, trigger_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    await manager.disconnect_user_from_trigger(str(current_user.id), trigger_id)