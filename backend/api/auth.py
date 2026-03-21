from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from core.dependencies import get_db
from models.user import User
from schemas.user import UserCreate, UserRead, Token
from core.dependencies import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserRead)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    register_mail=user.email.strip().lower()
    result = await db.execute(select(User).where(User.email == register_mail))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user.password)

    new_user = User(
        email=register_mail,
        password_hash=hashed_password
    )

    db.add(new_user)

    await db.commit()
    await db.refresh(new_user)
    
    return new_user

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    
    login_mail=form_data.username.strip().lower()
    statement=select(User).where(User.email == login_mail)
    
    result = await db.execute(statement)
    db_user = result.scalars().first()
    
    if not db_user or not verify_password(form_data.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
