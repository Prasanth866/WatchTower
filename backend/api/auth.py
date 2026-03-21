from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from core.security import get_password_hash, verify_password, create_access_token, decode_access_token
from core.dependencies import get_db
from models.user import User
from schemas.user import UserCreate, UserRead, Token, TokenData
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
