from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.schemas import TestCaseCreate, TestCaseUpdate, TestCaseOut
from src.services.pytest_service import PytestService
from src.core.deps import get_db, get_current_active_user
from src.models.user import User


router = APIRouter()


@router.post("", response_model=TestCaseOut)
async def create_pytest(
    pytest_item: TestCaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await PytestService.create_pytest(db, pytest_item, current_user.id)


@router.get("", response_model=List[TestCaseOut])
async def get_pytests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await PytestService.get_pytests(db, skip, limit)


@router.get("/{pytest_id}", response_model=TestCaseOut)
async def get_pytest(
    pytest_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    pytest_item = await PytestService.get_pytest(db, pytest_id)
    if not pytest_item:
        raise HTTPException(status_code=404, detail="Pytest item not found")
    return pytest_item


@router.put("/{pytest_id}", response_model=TestCaseOut)
async def update_pytest(
    pytest_id: int,
    pytest_update: TestCaseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    updated_pytest = await PytestService.update_pytest(db, pytest_id, pytest_update)
    if not updated_pytest:
        raise HTTPException(status_code=404, detail="Pytest item not found")
    return updated_pytest


@router.delete("/{pytest_id}")
async def delete_pytest(
    pytest_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    success = await PytestService.delete_pytest(db, pytest_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pytest item not found")
    return {"message": "Pytest item deleted successfully"}


@router.post("/{pytest_id}/execute")
async def execute_pytest(
    pytest_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await PytestService.execute_pytest(db, pytest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pytest item not found")
    return {"message": "Pytest executed successfully", "result": result}
