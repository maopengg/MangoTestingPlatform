from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.schemas.user import UserCreate, UserOut, Token
from src.models.user import User
from src.core.security import verify_password, create_access_token
from src.core.deps import get_db
from src.core.config import settings
from src.services.user_service import UserService


router = APIRouter()


@router.post(""/token"", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=""Incorrect username or password"",
            headers={""WWW-Authenticate"": ""Bearer""},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={""sub"": user.username}, expires_delta=access_token_expires
    )
    
    return {""access_token"": access_token, ""token_type"": ""bearer""}


@router.post(""/register"", response_model=UserOut)
async def register_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if user already exists
    result = await db.execute(select(User).filter(User.username == user.username))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=""Username already registered""
        )
    
    result = await db.execute(select(User).filter(User.email == user.email))
    existing_email = result.scalar_one_or_none()
    
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=""Email already registered""
        )
    
    db_user = await UserService.create_user(db, user)
    return db_user


@router.get(""/profile"", response_model=UserOut)
async def read_profile(
    current_user: User = Depends(UserService.get_current_active_user)
):
    return current_user
