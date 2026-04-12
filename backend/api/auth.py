"""This module defines the authentication API endpoints for register, login, and me """
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from core.security import get_password_hash, create_access_token
from core.dependencies import get_db
from core.dependencies import get_current_user
from models.user import User
from schemas.user import UserCreate, UserRead, Token, ForgotPasswordRequest, ResetPasswordRequest
from services.auth_service import authenticate_user, register_user
from services.password_reset_service import request_password_reset, reset_password

router = APIRouter()

@router.post("/register", response_model=UserRead)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers new user account."""
    return await register_user(
        db=db,
        email=user.email,
        password_hash=get_password_hash(user.password),
    )

@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
    ):
    """Authenticates a user and issues a JWT access token."""
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
    await request_password_reset(payload.email, db)
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await reset_password(payload.token, payload.new_password, db)
    return {"message": "Password reset successfully. Please log in."}
