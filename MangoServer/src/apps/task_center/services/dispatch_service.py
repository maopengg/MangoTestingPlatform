from django.db import transaction
from django.utils import timezone

from src.apps.auto_system.models import Tasks, TasksDetails
from src.apps.auto_system.service.tasks.add_tasks import AddTasks
from src.common.enums.tools_enum import TestCaseTypeEnum
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.services.schedule_fire_service import ScheduleFireService
from src.common.tools.log_collector import log


class ScheduleDispatchService:
    @classmethod
    def claim_pending_fire(cls, node_name: str | None = None) -> ScheduleFire | None:
        fire = ScheduleFire.objects.filter(
            status=ScheduleFireStatusEnum.PENDING.value,
            source_type=ScheduleFireSourceTypeEnum.TEST_SUITE.value,
        ).order_by('planned_at', 'id').first()
        if not fire:
            return None
        updated = ScheduleFire.objects.filter(
            id=fire.id,
            status=ScheduleFireStatusEnum.PENDING.value,
        ).update(
            status=ScheduleFireStatusEnum.DISPATCHING.value,
            dispatcher_node=node_name,
            update_time=timezone.now(),
        )
        if updated != 1:
            return None
        return ScheduleFire.objects.select_related('task').get(id=fire.id)

    @classmethod
    def dispatch_fire(cls, fire: ScheduleFire, node_name: str | None = None) -> int | None:
        if fire.source_type != ScheduleFireSourceTypeEnum.TEST_SUITE.value:
            ScheduleFire.objects.filter(id=fire.id).update(
                status=ScheduleFireStatusEnum.SKIPPED.value,
                error_message='当前分发器只处理测试套定时触发',
                update_time=timezone.now(),
            )
            return None
        if not fire.task_id:
            ScheduleFireService.mark_failed(fire.id, '定时触发记录缺少 task_id', node_name)
            return None
        try:
            with transaction.atomic():
                task = Tasks.objects.select_related('project_product', 'case_people').get(id=fire.task_id)
                test_suite_id = cls.create_test_suite(task)
                ScheduleFire.objects.filter(id=fire.id).update(
                    status=ScheduleFireStatusEnum.DISPATCHED.value,
                    test_suite_id=test_suite_id,
                    dispatcher_node=node_name,
                    update_time=timezone.now(),
                )
                return test_suite_id
        except Exception as error:
            log.system.error(f'分发定时触发记录失败：fire_id={fire.id}, error={error}')
            ScheduleFireService.mark_failed(fire.id, str(error), node_name)
            return None

    @classmethod
    def create_test_suite(cls, task: Tasks) -> int:
        add_tasks = AddTasks(
            project_product=task.project_product_id,
            test_env=task.test_env,
            is_notice=task.is_notice,
            user_id=task.case_people_id,
            tasks_id=task.id,
        )
        for detail in TasksDetails.objects.select_related('ui_case', 'api_case', 'pytest_case').filter(task=task.id):
            log.system.debug(f'分发定时任务详情：task_detail_id={detail.id}')
            if detail.type == TestCaseTypeEnum.API.value and detail.api_case_id:
                add_tasks.add_test_suite_details(detail.api_case_id, TestCaseTypeEnum.API)
            elif detail.type == TestCaseTypeEnum.UI.value and detail.ui_case_id:
                add_tasks.add_test_suite_details(detail.ui_case_id, TestCaseTypeEnum.UI)
            elif detail.pytest_case_id:
                add_tasks.add_test_suite_details(detail.pytest_case_id, TestCaseTypeEnum.PYTEST)
        return add_tasks.test_suite_id
