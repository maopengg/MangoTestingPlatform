from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.schemas import ApiTestCreate, ApiTestUpdate, ApiTestOut
from src.services.api_test_service import ApiTestService
from src.core.deps import get_db, get_current_active_user
from src.models.user import User


router = APIRouter()


@router.post("", response_model=ApiTestOut)
async def create_api_test(
    api_test: ApiTestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await ApiTestService.create_api_test(db, api_test, current_user.id)


@router.get("", response_model=List[ApiTestOut])
async def get_api_tests(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await ApiTestService.get_api_tests(db, skip, limit)


@router.get("/{api_test_id}", response_model=ApiTestOut)
async def get_api_test(
    api_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    api_test = await ApiTestService.get_api_test(db, api_test_id)
    if not api_test:
        raise HTTPException(status_code=404, detail="API test not found")
    return api_test


@router.put("/{api_test_id}", response_model=ApiTestOut)
async def update_api_test(
    api_test_id: int,
    api_test_update: ApiTestUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    updated_api_test = await ApiTestService.update_api_test(db, api_test_id, api_test_update)
    if not updated_api_test:
        raise HTTPException(status_code=404, detail="API test not found")
    return updated_api_test


@router.delete("/{api_test_id}")
async def delete_api_test(
    api_test_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    success = await ApiTestService.delete_api_test(db, api_test_id)
    if not success:
        raise HTTPException(status_code=404, detail="API test not found")
    return {"message": "API test deleted successfully"}
