from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models import MonitoringTask, MonitoringReport
from src.schemas import MonitoringTaskCreate, MonitoringTaskUpdate
import asyncio
import json
import datetime


class MonitoringService:
    @staticmethod
    async def get_monitoring_task(db_session: AsyncSession, task_id: int) -> Optional[MonitoringTask]:
        result = await db_session.execute(select(MonitoringTask).where(MonitoringTask.id == task_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_monitoring_tasks(db_session: AsyncSession, skip: int = 0, limit: int = 100) -> List[MonitoringTask]:
        result = await db_session.execute(select(MonitoringTask).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_monitoring_task(db_session: AsyncSession, task: MonitoringTaskCreate) -> MonitoringTask:
        db_task = MonitoringTask(
            name=task.name,
            description=task.description,
            script_content=task.script_content,
            cron_expression=task.cron_expression,
            is_active=task.is_active
        )
        db_session.add(db_task)
        await db_session.commit()
        await db_session.refresh(db_task)
        return db_task

    @staticmethod
    async def update_monitoring_task(db_session: AsyncSession, task_id: int, task_update: MonitoringTaskUpdate) -> Optional[MonitoringTask]:
        db_task = await MonitoringService.get_monitoring_task(db_session, task_id)
        if db_task:
            for key, value in task_update.dict(exclude_unset=True).items():
                setattr(db_task, key, value)
            await db_session.commit()
            await db_session.refresh(db_task)
        return db_task

    @staticmethod
    async def delete_monitoring_task(db_session: AsyncSession, task_id: int) -> bool:
        db_task = await MonitoringService.get_monitoring_task(db_session, task_id)
        if db_task:
            await db_session.delete(db_task)
            await db_session.commit()
            return True
        return False

    @staticmethod
    async def execute_monitoring_task(db_session: AsyncSession, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Execute a monitoring task
        """
        task = await MonitoringService.get_monitoring_task(db_session, task_id)
        if not task:
            return None

        # In a real implementation, this would execute the actual monitoring script
        # Here we'll simulate monitoring execution
        start_time = asyncio.get_event_loop().time()
        
        # Simulate some monitoring activity
        await asyncio.sleep(0.2)  # Simulate processing time
        
        # Generate a mock result
        result_data = {
            "status": "success",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "metrics": {
                "response_time": 125.4,
                "availability": 100.0,
                "error_rate": 0.0,
                "latency": 85.2
            },
            "checks": [
                {"name": "HTTP Status Check", "status": "passed"},
                {"name": "Response Time Check", "status": "passed"},
                {"name": "Content Validation", "status": "passed"}
            ]
        }

        # Create a monitoring report
        report = MonitoringReport(
            monitoring_task_id=task.id,
            status="success",
            report_data=json.dumps(result_data)
        )
        
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        return {
            "task_id": task.id,
            "task_name": task.name,
            "status": "completed",
            "result": result_data,
            "report_id": report.id
        }

    @staticmethod
    async def get_monitoring_report(db_session: AsyncSession, report_id: int) -> Optional[MonitoringReport]:
        result = await db_session.execute(select(MonitoringReport).where(MonitoringReport.id == report_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_monitoring_reports_by_task(db_session: AsyncSession, task_id: int, skip: int = 0, limit: int = 100) -> List[MonitoringReport]:
        result = await db_session.execute(
            select(MonitoringReport)
            .where(MonitoringReport.monitoring_task_id == task_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
