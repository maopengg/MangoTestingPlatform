from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.database.session import AsyncSessionLocal
from src.models.user import User
from src.core.security import verify_token
from src.core.exceptions import AuthenticationException


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=""/auth/token"")


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=""Could not validate credentials"",
        headers={""WWW-Authenticate"": ""Bearer""},
    )
    try:
        payload = verify_token(token)
        username: str = payload.get(""username"")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()
        
        if user is None:
            raise credentials_exception
        return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail=""Inactive user"")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail=""The user doesn't have enough privileges"")
    return current_user
