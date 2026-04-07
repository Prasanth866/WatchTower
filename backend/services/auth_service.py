from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import verify_password
from models.user import User


async def register_user(db: AsyncSession, email: str, password_hash: str) -> User:
    normalized_email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    existing_user = result.scalars().first()
    if existing_user:
        raise ValueError("Email already registered")

    new_user = User(email=normalized_email, password_hash=password_hash)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    normalized_email = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    db_user = result.scalars().first()

    if not db_user or not verify_password(password, db_user.password_hash):
        return None

    return db_user
