from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import ApiTest
from src.schemas import ApiTestCreate, ApiTestUpdate


class ApiTestService:
    @staticmethod
    async def get_api_test(db_session: AsyncSession, api_test_id: int) -> Optional[ApiTest]:
        result = await db_session.execute(select(ApiTest).where(ApiTest.id == api_test_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_api_tests(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[ApiTest]:
        result = await db_session.execute(select(ApiTest).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_api_test(db_session: AsyncSession, api_test: ApiTestCreate, user_id: int) -> ApiTest:
        # 获取项目以确认用户有权访问该项目
        # 这里可以添加额外的验证逻辑
        db_api_test = ApiTest(
            name=api_test.name,
            description=api_test.description,
            url=api_test.url,
            method=api_test.method.upper(),  # 标准化为大写
            headers=api_test.headers,
            body=api_test.body,
            project_id=api_test.project_id
        )
        db_session.add(db_api_test)
        await db_session.commit()
        await db_session.refresh(db_api_test)
        return db_api_test

    @staticmethod
    async def update_api_test(db_session: AsyncSession, api_test_id: int, api_test_update: ApiTestUpdate) -> Optional[ApiTest]:
        db_api_test = await ApiTestService.get_api_test(db_session, api_test_id)
        if db_api_test:
            for key, value in api_test_update.dict(exclude_unset=True).items():
                setattr(db_api_test, key, value)
            await db_session.commit()
            await db_session.refresh(db_api_test)
        return db_api_test

    @staticmethod
    async def delete_api_test(db_session: AsyncSession, api_test_id: int) -> bool:
        db_api_test = await ApiTestService.get_api_test(db_session, api_test_id)
        if db_api_test:
            await db_session.delete(db_api_test)
            await db_session.commit()
            return True
        return False
