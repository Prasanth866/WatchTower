from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_admin_user, get_db
from core.logger import get_logger
from models.email_queue import EmailQueue
from models.topic_subscription import TopicSubscription
from models.trigger import Trigger
from models.user import User
from schemas.admin import (
    AdminStatsRead,
    AdminTopicRead,
    AdminTriggerRead,
    AdminUserList,
    AdminUserRead,
)

router = APIRouter()
log = get_logger(__name__)


@router.get("/stats", response_model=AdminStatsRead)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    total_users = await db.scalar(select(func.count(User.id))) or 0
    total_subscriptions = await db.scalar(select(func.count(TopicSubscription.id))) or 0
    total_triggers = await db.scalar(select(func.count(Trigger.id))) or 0
    active_triggers = await db.scalar(
        select(func.count(Trigger.id)).where(Trigger.is_active.is_(True))
    ) or 0
    pending_emails = await db.scalar(
        select(func.count(EmailQueue.id)).where(EmailQueue.sent.is_(False))
    ) or 0
    return AdminStatsRead(
        total_users=total_users,
        total_subscriptions=total_subscriptions,
        total_triggers=total_triggers,
        active_triggers=active_triggers,
        pending_emails=pending_emails,
    )


@router.get("/users", response_model=AdminUserList)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = list(result.scalars().all())
    total = await db.scalar(select(func.count(User.id))) or 0
    return AdminUserList(users=users, total=total)


@router.get("/users/{user_id}", response_model=AdminUserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/users/{user_id}/toggle-admin", response_model=AdminUserRead)
async def toggle_admin(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user),
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify your own admin status",
        )
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_admin = not user.is_admin
    await db.commit()
    await db.refresh(user)
    log.info("admin_toggled", target_user=str(user_id), is_admin=user.is_admin)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_admin_user),
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()
    log.info("user_deleted_by_admin", target_user=str(user_id))


@router.get("/subscriptions", response_model=list[AdminTopicRead])
async def list_all_subscriptions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    result = await db.execute(
        select(TopicSubscription).order_by(TopicSubscription.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/subscriptions/by-topic")
async def subscriptions_by_topic(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    result = await db.execute(
        select(TopicSubscription.topic, func.count(TopicSubscription.id).label("count"))
        .group_by(TopicSubscription.topic)
        .order_by(func.count(TopicSubscription.id).desc())
    )
    return [{"topic": row.topic, "count": row.count} for row in result.all()]


@router.get("/triggers", response_model=list[AdminTriggerRead])
async def list_all_triggers(
    skip: int = 0,
    limit: int = 50,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    query = select(Trigger).order_by(Trigger.created_at.desc())
    if active_only:
        query = query.where(Trigger.is_active.is_(True))
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


@router.delete("/triggers/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_trigger(
    trigger_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    trigger = await db.get(Trigger, trigger_id)
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")
    await db.delete(trigger)
    await db.commit()


@router.get("/connections")
async def live_connections(
    request: Request,
    _: User = Depends(get_admin_user),
):
    manager = request.app.state.manager
    return manager.get_connection_counts()