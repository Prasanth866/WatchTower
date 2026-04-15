"""This module provides security utilities for password hashing and JWT token management."""
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from core.config import get_settings
setting=get_settings()
SECRET_KEY = setting.SECRET_KEY
ALGORITHM = setting.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = setting.ACCESS_TOKEN_EXPIRE_MINUTES

def get_password_hash(password: str) -> str:
    """Hash the given password using bcrypt."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that the provided plain password matches the hashed password."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with the given data and expiration time."""
    to_encode = data.copy()
    expire = (  datetime.now(timezone.utc)
                            +
                ( expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
            )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    """Decode the JWT access token and return the payload if valid, otherwise return None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
