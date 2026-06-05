from datetime import datetime
from uuid import uuid4

from django.db import IntegrityError
from django.utils import timezone

from src.apps.auto_system.models import Tasks, TimeTasks
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.models import ScheduleFire
from src.common.tools.log_collector import log


class ScheduleFireService:
    @staticmethod
    def build_fire_key(source_type: int, business_key: str, planned_at: datetime) -> str:
        return f'{source_type}:{business_key}:{planned_at.strftime("%Y%m%d%H%M")}'

    @classmethod
    def create_test_suite_fire(cls, task: Tasks, planned_at: datetime, node_name: str | None = None) -> tuple[ScheduleFire | None, bool]:
        source_type = ScheduleFireSourceTypeEnum.TEST_SUITE.value
        try:
            fire = ScheduleFire.objects.create(
                fire_key=cls.build_fire_key(source_type, f'task:{task.id}', planned_at),
                time_task_id=task.timing_strategy_id,
                task_id=task.id,
                task_name=task.name,
                planned_at=planned_at,
                fired_at=timezone.now(),
                source_type=source_type,
                status=ScheduleFireStatusEnum.PENDING.value,
                trigger_node=node_name,
            )
            return fire, True
        except IntegrityError:
            log.system.info(f'定时任务已触发，跳过重复记录：task_id={task.id}, planned_at={planned_at}')
            return None, False

    @classmethod
    def create_token_refresh_fire(cls, time_task: TimeTasks, planned_at: datetime, node_name: str | None = None) -> tuple[ScheduleFire | None, bool]:
        return cls.create_system_fire(
            source_type=ScheduleFireSourceTypeEnum.TOKEN_REFRESH.value,
            business_key=f'time_task:{time_task.id}',
            task_name=f'API授权Token刷新：{time_task.name}',
            planned_at=planned_at,
            node_name=node_name,
            time_task=time_task,
        )

    @classmethod
    def create_data_cleanup_fire(cls, job_name: str, planned_at: datetime, node_name: str | None = None) -> tuple[ScheduleFire | None, bool]:
        return cls.create_system_fire(
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            business_key=job_name,
            task_name=job_name,
            planned_at=planned_at,
            node_name=node_name,
            extra_data={'job_key': job_name},
        )

    @classmethod
    def create_system_job_fire(cls, job_name: str, planned_at: datetime, node_name: str | None = None) -> tuple[ScheduleFire | None, bool]:
        return cls.create_system_fire(
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            business_key=job_name,
            task_name=job_name,
            planned_at=planned_at,
            node_name=node_name,
            extra_data={'job_key': job_name},
        )

    @classmethod
    def create_manual_system_fire(
            cls,
            source_type: int,
            job_name: str,
            task_name: str,
            planned_at: datetime,
            node_name: str | None = None,
    ) -> ScheduleFire:
        return ScheduleFire.objects.create(
            fire_key=cls.build_fire_key(source_type, f'manual:{job_name}:{uuid4().hex}', planned_at),
            task_name=task_name,
            planned_at=planned_at,
            fired_at=timezone.now(),
            source_type=source_type,
            status=ScheduleFireStatusEnum.DISPATCHING.value,
            trigger_node=node_name,
            dispatcher_node=node_name,
            extra_data={'trigger_mode': 'manual'},
        )

    @classmethod
    def create_system_fire(
            cls,
            source_type: int,
            business_key: str,
            task_name: str,
            planned_at: datetime,
            node_name: str | None = None,
            time_task: TimeTasks | None = None,
            extra_data: dict | None = None,
    ) -> tuple[ScheduleFire | None, bool]:
        try:
            fire = ScheduleFire.objects.create(
                fire_key=cls.build_fire_key(source_type, business_key, planned_at),
                time_task=time_task,
                task_name=task_name,
                planned_at=planned_at,
                fired_at=timezone.now(),
                source_type=source_type,
                status=ScheduleFireStatusEnum.DISPATCHING.value,
                trigger_node=node_name,
                dispatcher_node=node_name,
                extra_data=extra_data or {},
            )
            return fire, True
        except IntegrityError:
            log.system.info(f'系统定时任务已触发，跳过重复记录：source_type={source_type}, key={business_key}, planned_at={planned_at}')
            return None, False

    @classmethod
    def mark_failed(cls, fire_id: int, error_message: str, node_name: str | None = None):
        ScheduleFire.objects.filter(id=fire_id).update(
            status=ScheduleFireStatusEnum.FAIL.value,
            error_message=error_message,
            dispatcher_node=node_name,
            update_time=timezone.now(),
        )

    @classmethod
    def mark_success(cls, fire_id: int, node_name: str | None = None, extra_data: dict | None = None):
        update_data = {
            'status': ScheduleFireStatusEnum.SUCCESS.value,
            'dispatcher_node': node_name,
            'update_time': timezone.now(),
        }
        if extra_data is not None:
            fire = ScheduleFire.objects.filter(id=fire_id).only('extra_data').first()
            current_extra_data = fire.extra_data if fire and isinstance(fire.extra_data, dict) else {}
            current_extra_data.update(extra_data)
            update_data['extra_data'] = current_extra_data
        ScheduleFire.objects.filter(id=fire_id).update(**update_data)
