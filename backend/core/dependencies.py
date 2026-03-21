from typing import AsyncGenerator
from fastapi import HTTPException,status,Depends
from pydantic_core import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from schemas.user import TokenData
from services.database import async_session
from fastapi.security import OAuth2PasswordBearer
from core.security import decode_access_token

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
            yield session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_access_token(token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}, 
    )
    if payload is None:
        raise credentials_exception
    
    token_sub = payload.get("sub")
    if token_sub is None:
        raise credentials_exception
        
    try:
        token_data = TokenData(user_id=token_sub)
    except (ValueError,ValidationError):
        raise credentials_exception

    user = await db.get(User, token_data.user_id)
    
    if user is None:
        raise credentials_exception        
    
    return user


