import asyncio
import sys

from sqlalchemy import select

from core.database import async_session
from core.security import get_password_hash
from models.user import User


async def create_admin(email: str, password: str) -> None:
    normalized_email = email.strip().lower()
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == normalized_email))
        user = result.scalar_one_or_none()
        if user:
            user.is_admin = True
            await db.commit()
            print(f"Promoted {normalized_email} to admin")
            return

        user = User(
            email=normalized_email,
            password_hash=get_password_hash(password),
            is_admin=True,
        )
        db.add(user)
        await db.commit()
        print(f"Created admin: {normalized_email}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <email> <password>")
        raise SystemExit(1)
    asyncio.run(create_admin(sys.argv[1], sys.argv[2]))