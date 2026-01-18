from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from src.schemas import ProjectCreate, ProjectUpdate, ProjectOut
from src.services.task_service import TaskService
from src.core.deps import get_db, get_current_active_user
from src.models.user import User


router = APIRouter()


@router.post("/projects", response_model=ProjectOut)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await TaskService.create_project(db, project, current_user.id)


@router.get("/projects", response_model=List[ProjectOut])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await TaskService.get_projects(db, skip, limit)


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    project = await TaskService.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    updated_project = await TaskService.update_project(db, project_id, project_update)
    if not updated_project:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated_project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    success = await TaskService.delete_project(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}


# Task management endpoints
@router.post("/tasks", response_model=dict)
async def create_task(
    task_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await TaskService.create_task(db, task_data, current_user.id)


@router.get("/tasks", response_model=List[dict])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await TaskService.get_tasks(db, skip, limit)


@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await TaskService.execute_task(db, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task executed successfully", "result": result}


@router.post("/tasks/{task_id}/schedule")
async def schedule_task(
    task_id: int,
    schedule_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await TaskService.schedule_task(db, task_id, schedule_data)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task scheduled successfully", "result": result}
