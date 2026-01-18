from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import TestCase
from src.schemas import TestCaseCreate, TestCaseUpdate


class UITestService:
    @staticmethod
    async def get_ui_test(db_session: AsyncSession, ui_test_id: int) -> Optional[TestCase]:
        result = await db_session.execute(select(TestCase).where(TestCase.id == ui_test_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_ui_tests(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[TestCase]:
        result = await db_session.execute(select(TestCase).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_ui_test(db_session: AsyncSession, ui_test: TestCaseCreate, user_id: int) -> TestCase:
        db_ui_test = TestCase(
            name=ui_test.name,
            description=ui_test.description,
            steps=ui_test.steps,
            project_id=ui_test.project_id
        )
        db_session.add(db_ui_test)
        await db_session.commit()
        await db_session.refresh(db_ui_test)
        return db_ui_test

    @staticmethod
    async def update_ui_test(db_session: AsyncSession, ui_test_id: int, ui_test_update: TestCaseUpdate) -> Optional[TestCase]:
        db_ui_test = await UITestService.get_ui_test(db_session, ui_test_id)
        if db_ui_test:
            for key, value in ui_test_update.dict(exclude_unset=True).items():
                setattr(db_ui_test, key, value)
            await db_session.commit()
            await db_session.refresh(db_ui_test)
        return db_ui_test

    @staticmethod
    async def delete_ui_test(db_session: AsyncSession, ui_test_id: int) -> bool:
        db_ui_test = await UITestService.get_ui_test(db_session, ui_test_id)
        if db_ui_test:
            await db_session.delete(db_ui_test)
            await db_session.commit()
            return True
        return False
