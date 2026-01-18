from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.schemas import TestCaseCreate, TestCaseUpdate, TestCaseOut
from src.services.ui_test_service import UITestService
from src.core.deps import get_db, get_current_active_user
from src.models.user import User


router = APIRouter()


@router.post("", response_model=TestCaseOut)
async def create_ui_test(
    ui_test: TestCaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await UITestService.create_ui_test(db, ui_test, current_user.id)


@router.get("", response_model=List[TestCaseOut])
async def get_ui_tests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await UITestService.get_ui_tests(db, skip, limit)


@router.get("/{ui_test_id}", response_model=TestCaseOut)
async def get_ui_test(
    ui_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    ui_test = await UITestService.get_ui_test(db, ui_test_id)
    if not ui_test:
        raise HTTPException(status_code=404, detail="UI test not found")
    return ui_test


@router.put("/{ui_test_id}", response_model=TestCaseOut)
async def update_ui_test(
    ui_test_id: int,
    ui_test_update: TestCaseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    updated_ui_test = await UITestService.update_ui_test(db, ui_test_id, ui_test_update)
    if not updated_ui_test:
        raise HTTPException(status_code=404, detail="UI test not found")
    return updated_ui_test


@router.delete("/{ui_test_id}")
async def delete_ui_test(
    ui_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    success = await UITestService.delete_ui_test(db, ui_test_id)
    if not success:
        raise HTTPException(status_code=404, detail="UI test not found")
    return {"message": "UI test deleted successfully"}
