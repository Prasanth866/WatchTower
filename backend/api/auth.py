"""This module defines the authentication API endpoints for register, login, and me """
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_password_hash, create_access_token
from core.dependencies import get_db
from core.dependencies import get_current_user
from core.rate_limiter import limiter
from models.user import User
from schemas.user import (
    ForgotPasswordRequest,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserRead,
)
from services.auth_service import authenticate_user, register_user
from services.password_reset_service import request_password_reset, reset_password

router = APIRouter()

@router.post("/register", response_model=UserRead)
@limiter.limit("5/minute")
async def register(request: Request, user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers new user account."""
    _ = request
    return await register_user(
        db=db,
        email=user.email,
        password_hash=get_password_hash(user.password),
    )

@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
    ):
    """Authenticates a user and issues a JWT access token."""
    _ = request
    db_user = await authenticate_user(db, form_data.username, form_data.password)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(db_user.id)})

    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """Returns the currently authenticated user's information."""
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initiates the password reset process by sending a reset link to the user's email."""
    await request_password_reset(payload.email, db)
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Resets the user's password using the provided token and new password."""
    await reset_password(payload.token, payload.new_password, db)
    return {"message": "Password reset successfully. Please log in."}


@router.patch("/notifications", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    payload: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Updates the user's notification preferences."""
    current_user.email_notifications = payload.email_notifications
    await db.commit()
    await db.refresh(current_user)
    return NotificationPreferenceResponse(email_notifications=current_user.email_notifications)
