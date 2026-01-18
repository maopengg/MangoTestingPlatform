from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.schemas import MonitoringTaskCreate, MonitoringTaskUpdate, MonitoringTaskOut
from src.services.monitoring_service import MonitoringService
from src.core.deps import get_db, get_current_active_user
from src.models.user import User


router = APIRouter()


@router.post("/tasks", response_model=MonitoringTaskOut)
async def create_monitoring_task(
    monitoring_task: MonitoringTaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await MonitoringService.create_monitoring_task(db, monitoring_task)


@router.get("/tasks", response_model=List[MonitoringTaskOut])
async def get_monitoring_tasks(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await MonitoringService.get_monitoring_tasks(db, skip, limit)


@router.get("/tasks/{task_id}", response_model=MonitoringTaskOut)
async def get_monitoring_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    task = await MonitoringService.get_monitoring_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Monitoring task not found")
    return task


@router.put("/tasks/{task_id}", response_model=MonitoringTaskOut)
async def update_monitoring_task(
    task_id: int,
    monitoring_task_update: MonitoringTaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    updated_task = await MonitoringService.update_monitoring_task(db, task_id, monitoring_task_update)
    if not updated_task:
        raise HTTPException(status_code=404, detail="Monitoring task not found")
    return updated_task


@router.delete("/tasks/{task_id}")
async def delete_monitoring_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    success = await MonitoringService.delete_monitoring_task(db, task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Monitoring task not found")
    return {"message": "Monitoring task deleted successfully"}


@router.post("/tasks/{task_id}/execute")
async def execute_monitoring_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await MonitoringService.execute_monitoring_task(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Monitoring task not found")
    return {"message": "Monitoring task executed successfully", "result": result}


@router.get("/reports/{report_id}")
async def get_monitoring_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    report = await MonitoringService.get_monitoring_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Monitoring report not found")
    return report


@router.get("/reports/task/{task_id}")
async def get_monitoring_reports_by_task(
    task_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    reports = await MonitoringService.get_monitoring_reports_by_task(db, task_id, skip, limit)
    return reports
