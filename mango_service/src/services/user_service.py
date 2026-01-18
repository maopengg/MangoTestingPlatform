from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.security import hash_password


class UserService:
    @staticmethod
    async def get_user(db_session: AsyncSession, user_id: int) -> Optional[User]:
        result = await db_session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_username(db_session: AsyncSession, username: str) -> Optional[User]:
        result = await db_session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_users(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        result = await db_session.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_user(db_session: AsyncSession, user: UserCreate) -> User:
        hashed_password = hash_password(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        db_session.add(db_user)
        await db_session.commit()
        await db_session.refresh(db_user)
        return db_user

    @staticmethod
    async def update_user(db_session: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
        db_user = await UserService.get_user(db_session, user_id)
        if db_user:
            for key, value in user_update.dict(exclude_unset=True).items():
                setattr(db_user, key, value)
            await db_session.commit()
            await db_session.refresh(db_user)
        return db_user

    @staticmethod
    async def delete_user(db_session: AsyncSession, user_id: int) -> bool:
        db_user = await UserService.get_user(db_session, user_id)
        if db_user:
            await db_session.delete(db_user)
            await db_session.commit()
            return True
        return False
