"""Pydantic models for user creation, reading, and authentication token management."""
import uuid
from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator

class UserCreate(BaseModel):
    """Pydantic model for creating a new user."""
    email: EmailStr=Field(description="The user's unique email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description=(
            "Password must be 8-72 characters long and include: "
            "one uppercase letter, one lowercase letter, one number, "
            "and one special character (!@#$%^&*...)"
        )
    )

    @field_validator("password")
    def password_complexity(cls, v: str) -> str:
        """Validator to enforce password complexity requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

class UserRead(BaseModel):
    """Pydantic model for reading user information, excluding sensitive data like password hash."""
    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    """Pydantic model for representing an authentication token"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Pydantic model for representing data extracted from an authentication token"""
    user_id: Optional[uuid.UUID] = None
