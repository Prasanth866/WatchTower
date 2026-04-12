"""Pydantic models for user creation, reading, and authentication token management."""
import uuid
from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator


def _validate_password_complexity(value: str) -> str:
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValueError("Password must contain at least one special character")
    return value

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
        return _validate_password_complexity(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        _validate_password_complexity(self.new_password)
        return self

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
