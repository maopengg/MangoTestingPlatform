from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import TestCase
from src.schemas import TestCaseCreate, TestCaseUpdate
import subprocess
import tempfile
import os


class PytestService:
    @staticmethod
    async def get_pytest(db_session: AsyncSession, pytest_id: int) -> Optional[TestCase]:
        result = await db_session.execute(select(TestCase).where(TestCase.id == pytest_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_pytests(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[TestCase]:
        result = await db_session.execute(select(TestCase).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_pytest(db_session: AsyncSession, pytest_item: TestCaseCreate, user_id: int) -> TestCase:
        db_pytest = TestCase(
            name=pytest_item.name,
            description=pytest_item.description,
            steps=pytest_item.steps,  # In this context, steps would contain the pytest code
            project_id=pytest_item.project_id
        )
        db_session.add(db_pytest)
        await db_session.commit()
        await db_session.refresh(db_pytest)
        return db_pytest

    @staticmethod
    async def update_pytest(db_session: AsyncSession, pytest_id: int, pytest_update: TestCaseUpdate) -> Optional[TestCase]:
        db_pytest = await PytestService.get_pytest(db_session, pytest_id)
        if db_pytest:
            for key, value in pytest_update.dict(exclude_unset=True).items():
                setattr(db_pytest, key, value)
            await db_session.commit()
            await db_session.refresh(db_pytest)
        return db_pytest

    @staticmethod
    async def delete_pytest(db_session: AsyncSession, pytest_id: int) -> bool:
        db_pytest = await PytestService.get_pytest(db_session, pytest_id)
        if db_pytest:
            await db_session.delete(db_pytest)
            await db_session.commit()
            return True
        return False

    @staticmethod
    async def execute_pytest(db_session: AsyncSession, pytest_id: int) -> Optional[Dict[str, Any]]:
        """
        Execute a pytest test case by ID
        """
        pytest_item = await PytestService.get_pytest(db_session, pytest_id)
        if not pytest_item:
            return None

        # If the test case contains actual pytest code in the steps field
        if pytest_item.steps:
            # Create a temporary file to execute the pytest code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(pytest_item.steps)
                temp_file_path = temp_file.name

            try:
                # Execute pytest on the temporary file
                result = subprocess.run([
                    'python', '-m', 'pytest', temp_file_path, '-v', '--tb=short'
                ], capture_output=True, text=True, timeout=30)

                return {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'success': result.returncode == 0
                }
            except subprocess.TimeoutExpired:
                return {
                    'error': 'Test execution timed out',
                    'success': False
                }
            except Exception as e:
                return {
                    'error': str(e),
                    'success': False
                }
            finally:
                # Clean up the temporary file
                os.unlink(temp_file_path)
        else:
            # If no code is provided, return an error
            return {
                'error': 'No test code provided',
                'success': False
            }
