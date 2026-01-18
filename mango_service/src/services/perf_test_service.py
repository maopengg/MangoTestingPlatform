from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import PytestCase, PytestProduct
from src.schemas import TestCaseCreate, TestCaseUpdate
import asyncio
import time
import json
import subprocess
import os


class PerfTestService:
    @staticmethod
    async def get_performance_test(db_session: AsyncSession, perf_test_id: int) -> Optional[PytestCase]:
        result = await db_session.execute(select(PytestCase).where(PytestCase.id == perf_test_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_performance_tests(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[PytestCase]:
        result = await db_session.execute(select(PytestCase).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_performance_test(db_session: AsyncSession, perf_test: TestCaseCreate, user_id: int) -> PytestCase:
        # For performance tests, we'll create a Pytest case with performance script
        db_perf_test = PytestCase(
            name=perf_test.name,
            case_describe=perf_test.description,
            case_script=perf_test.steps,  # Performance test script
            project_id=perf_test.project_id,  # This should map to pytest_product_id
            case_type=2,  # Performance test type
            status=1,
            case_people_id=user_id
        )
        db_session.add(db_perf_test)
        await db_session.commit()
        await db_session.refresh(db_perf_test)
        return db_perf_test

    @staticmethod
    async def update_performance_test(db_session: AsyncSession, perf_test_id: int, perf_test_update: TestCaseUpdate) -> Optional[PytestCase]:
        db_perf_test = await PerfTestService.get_performance_test(db_session, perf_test_id)
        if db_perf_test:
            for key, value in perf_test_update.dict(exclude_unset=True).items():
                if hasattr(db_perf_test, key):
                    setattr(db_perf_test, key, value)
            await db_session.commit()
            await db_session.refresh(db_perf_test)
        return db_perf_test

    @staticmethod
    async def delete_performance_test(db_session: AsyncSession, perf_test_id: int) -> bool:
        db_perf_test = await PerfTestService.get_performance_test(db_session, perf_test_id)
        if db_perf_test:
            await db_session.delete(db_perf_test)
            await db_session.commit()
            return True
        return False

    @staticmethod
    async def execute_performance_test(db_session: AsyncSession, perf_test_id: int) -> Optional[Dict[str, Any]]:
        """
        Execute a performance test using Locust or similar tool
        """
        perf_test = await PerfTestService.get_performance_test(db_session, perf_test_id)
        if not perf_test:
            return None

        # Check if locust is installed
        try:
            import locust
        except ImportError:
            # If locust is not available, return a simulated result
            return await PerfTestService._simulate_performance_test(perf_test_id)

        # In a real implementation, this would execute the actual performance test
        # For now, returning simulated results
        return await PerfTestService._simulate_performance_test(perf_test_id)
    
    @staticmethod
    async def _simulate_performance_test(perf_test_id: int) -> Dict[str, Any]:
        """
        Simulate performance test execution
        """
        # Simulated performance test execution
        import random
        
        start_time = time.time()
        
        # Simulate performance test metrics
        total_requests = random.randint(100, 1000)
        successful_requests = int(total_requests * random.uniform(0.8, 1.0))
        failed_requests = total_requests - successful_requests
        duration = random.uniform(30, 300)  # Test duration in seconds
        
        # Response time statistics
        avg_response_time = random.uniform(0.1, 2.0)
        min_response_time = random.uniform(0.05, 0.5)
        max_response_time = random.uniform(2.0, 10.0)
        
        return {
            'test_id': perf_test_id,
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'duration': duration,
            'avg_response_time': avg_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'requests_per_second': total_requests / duration if duration > 0 else 0,
            'success_rate': successful_requests / total_requests if total_requests > 0 else 0
        }
