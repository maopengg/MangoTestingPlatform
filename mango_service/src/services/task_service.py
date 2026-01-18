from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import Project, Task, TaskDetail
from src.schemas import ProjectCreate, ProjectUpdate
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
import asyncio
import json


class TaskService:
    # Class-level scheduler instance
    _scheduler = None

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
            jobstores = {
                'default': MemoryJobStore()
            }
            executors = {
                'default': ThreadPoolExecutor(20)
            }
            job_defaults = {
                'coalesce': False,
                'max_instances': 3
            }
            cls._scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults
            )
        return cls._scheduler

    @staticmethod
    async def get_project(db_session: AsyncSession, project_id: int) -> Optional[Project]:
        result = await db_session.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_projects(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[Project]:
        result = await db_session.execute(select(Project).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_project(db_session: AsyncSession, project: ProjectCreate, user_id: int) -> Project:
        db_project = Project(
            name=project.name,
            description=project.description,
            owner_id=user_id
        )
        db_session.add(db_project)
        await db_session.commit()
        await db_session.refresh(db_project)
        return db_project

    @staticmethod
    async def update_project(db_session: AsyncSession, project_id: int, project_update: ProjectUpdate) -> Optional[Project]:
        db_project = await TaskService.get_project(db_session, project_id)
        if db_project:
            for key, value in project_update.dict(exclude_unset=True).items():
                setattr(db_project, key, value)
            await db_session.commit()
            await db_session.refresh(db_project)
        return db_project

    @staticmethod
    async def delete_project(db_session: AsyncSession, project_id: int) -> bool:
        db_project = await TaskService.get_project(db_session, project_id)
        if db_project:
            await db_session.delete(db_project)
            await db_session.commit()
            return True
        return False

    @staticmethod
    async def create_task(db_session: AsyncSession, task_data: dict, user_id: int) -> Dict[str, Any]:
        # Create a task in the database
        name = task_data.get('name', 'Unnamed Task')
        description = task_data.get('description', '')
        project_id = task_data.get('project_id')
        cron_expression = task_data.get('cron_expression')

        db_task = Task(
            name=name,
            description=description,
            project_id=project_id,
            cron_expression=cron_expression,
            is_active=True
        )

        db_session.add(db_task)
        await db_session.commit()
        await db_session.refresh(db_task)

        # If a cron expression is provided, schedule the task
        if cron_expression:
            scheduler = TaskService.get_scheduler()
            if not scheduler.running:
                scheduler.start()

            # Add the job to the scheduler
            job_id = f""task_{db_task.id}""
            scheduler.add_job(
                TaskService._execute_task_logic,
                'cron',
                id=job_id,
                cron=cron_expression,
                args=[db_task.id, db_session]
            )

        return {
            ""id"": db_task.id,
            ""name"": db_task.name,
            ""project_id"": db_task.project_id,
            ""cron_expression"": db_task.cron_expression,
            ""is_active"": db_task.is_active
        }

    @staticmethod
    async def get_tasks(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        result = await db_session.execute(select(Task).offset(skip).limit(limit))
        tasks = result.scalars().all()

        task_list = []
        for task in tasks:
            task_list.append({
                ""id"": task.id,
                ""name"": task.name,
                ""description"": task.description,
                ""project_id"": task.project_id,
                ""cron_expression"": task.cron_expression,
                ""is_active"": task.is_active
            })

        return task_list

    @staticmethod
    async def execute_task(db_session: AsyncSession, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Execute a specific task immediately
        """
        task_result = await db_session.execute(select(Task).where(Task.id == task_id))
        task = task_result.scalar_one_or_none()

        if not task:
            return None

        # In a real implementation, this would execute the actual task
        # Here we'll simulate task execution
        await asyncio.sleep(0.1)  # Simulate some processing time

        return {
            ""task_id"": task.id,
            ""name"": task.name,
            ""status"": ""completed"",
            ""executed_at"": ""2023-01-01T00:00:00Z"",
            ""result"": ""Task executed successfully""
        }

    @staticmethod
    async def schedule_task(db_session: AsyncSession, task_id: int, schedule_data: dict) -> Optional[Dict[str, Any]]:
        """
        Schedule a task with a specific cron expression
        """
        task_result = await db_session.execute(select(Task).where(Task.id == task_id))
        task = task_result.scalar_one_or_none()

        if not task:
            return None

        # Update the task with the new cron expression
        cron_expression = schedule_data.get('cron_expression')
        if cron_expression:
            task.cron_expression = cron_expression
            task.is_active = True
            await db_session.commit()
            await db_session.refresh(task)

            # Schedule the task in the scheduler
            scheduler = TaskService.get_scheduler()
            if not scheduler.running:
                scheduler.start()

            job_id = f""task_{task.id}""
            
            # Remove existing job if it exists
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)

            # Add the new job
            scheduler.add_job(
                TaskService._execute_task_logic,
                'cron',
                id=job_id,
                cron=cron_expression,
                args=[task.id, db_session]
            )

        return {
            ""task_id"": task.id,
            ""name"": task.name,
            ""cron_expression"": task.cron_expression,
            ""is_active"": task.is_active
        }

    @staticmethod
    async def _execute_task_logic(task_id: int, db_session: AsyncSession):
        """
        Internal method to execute task logic
        """
        # This would be called by the scheduler
        # In a real implementation, this would execute the actual task
        print(f""Executing task {task_id}..."")
        
        # Simulate task execution
        await asyncio.sleep(0.1)
        
        print(f""Task {task_id} completed."")
