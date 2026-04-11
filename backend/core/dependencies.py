"""Dependency functions for FastAPI routes, including session management and user authentication"""
from uuid import UUID
from typing import AsyncGenerator
from fastapi import HTTPException,status,Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic_core import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from core.database import async_session
from core.security import decode_access_token

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function to provide an async database session."""
    async with async_session() as session:
        yield session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
            token: str = Depends(oauth2_scheme),
            db: AsyncSession = Depends(get_db)
        ) -> User:
    """Dependency function to retrieve the current authenticated user based on JWT token"""
    payload = decode_access_token(token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if payload is None:
        raise credentials_exception
    token_id = payload.get("sub")
    if token_id is None:
        raise credentials_exception
    try:
        user_id = UUID(token_id)
    except (ValueError, ValidationError) as exc:
        raise credentials_exception from exc
    result = await db.get(User, user_id)
    if result is None:
        raise credentials_exception
    return result
