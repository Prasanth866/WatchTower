import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import get_settings
from core.exception import BadRequestException
from core.logger import get_logger
from core.security import get_password_hash
from models.password_reset import PasswordReset
from models.user import User
from services.email_service import queue_alert_email

log = get_logger(__name__)
settings = get_settings()
RESET_TOKEN_EXPIRE_MINUTES = 30


async def request_password_reset(email: str, db: AsyncSession) -> None:
    normalized_email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user:
        log.info("reset_requested_unknown_email", email=normalized_email)
        return

    existing = await db.execute(
        select(PasswordReset).where(
            PasswordReset.user_id == user.id,
            PasswordReset.used.is_(False),
        )
    )
    for old_token in existing.scalars().all():
        old_token.used = True

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    db.add(
        PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
            used=False,
        )
    )

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    await queue_alert_email(
        db=db,
        user_id=user.id,
        to_email=user.email,
        subject="WatchTower: Reset your password",
        body=(
            "You requested a password reset for your WatchTower account.\n\n"
            f"Reset link: {reset_link}\n\n"
            f"This link expires in {RESET_TOKEN_EXPIRE_MINUTES} minutes.\n"
            "If you did not request this, you can ignore this email."
        ),
    )

    await db.commit()
    log.info("reset_token_created", user_id=str(user.id))


async def reset_password(token: str, new_password: str, db: AsyncSession) -> None:
    result = await db.execute(select(PasswordReset).where(PasswordReset.token == token))
    reset = result.scalar_one_or_none()

    if not reset:
        raise BadRequestException("Invalid reset token")
    if reset.used:
        raise BadRequestException("Reset token already used")
    if datetime.now(timezone.utc) > reset.expires_at:
        raise BadRequestException("Reset token has expired")

    user = await db.get(User, reset.user_id)
    if not user:
        raise BadRequestException("User not found")

    user.password_hash = get_password_hash(new_password)
    reset.used = True

    await queue_alert_email(
        db=db,
        user_id=user.id,
        to_email=user.email,
        subject="WatchTower: Password reset successful",
        body="Your password has been reset successfully. If this was not you, contact support immediately.",
    )

    await db.commit()
    log.info("password_reset_success", user_id=str(user.id))
