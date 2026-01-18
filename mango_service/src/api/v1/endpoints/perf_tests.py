from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.schemas import TestCaseCreate, TestCaseUpdate, TestCaseOut
from src.services.perf_test_service import PerfTestService
from src.core.deps import get_db, get_current_active_user
from src.models import PytestCase as TestCaseOut
from src.models.user import User


router = APIRouter()


@router.post("", response_model=TestCaseOut)
async def create_performance_test(
    perf_test: TestCaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await PerfTestService.create_performance_test(db, perf_test, current_user.id)


@router.get("", response_model=List[TestCaseOut])
async def get_performance_tests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await PerfTestService.get_performance_tests(db, skip, limit)


@router.get("/{perf_test_id}", response_model=TestCaseOut)
async def get_performance_test(
    perf_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    perf_test = await PerfTestService.get_performance_test(db, perf_test_id)
    if not perf_test:
        raise HTTPException(status_code=404, detail="Performance test not found")
    return perf_test


@router.put("/{perf_test_id}", response_model=TestCaseOut)
async def update_performance_test(
    perf_test_id: int,
    perf_test_update: TestCaseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    updated_perf_test = await PerfTestService.update_performance_test(db, perf_test_id, perf_test_update)
    if not updated_perf_test:
        raise HTTPException(status_code=404, detail="Performance test not found")
    return updated_perf_test


@router.delete("/{perf_test_id}")
async def delete_performance_test(
    perf_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    success = await PerfTestService.delete_performance_test(db, perf_test_id)
    if not success:
        raise HTTPException(status_code=404, detail="Performance test not found")
    return {"message": "Performance test deleted successfully"}


@router.post("/{perf_test_id}/execute")
async def execute_performance_test(
    perf_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await PerfTestService.execute_performance_test(db, perf_test_id)
    if not result:
        raise HTTPException(status_code=404, detail="Performance test not found")
    return {"message": "Performance test executed successfully", "result": result}
