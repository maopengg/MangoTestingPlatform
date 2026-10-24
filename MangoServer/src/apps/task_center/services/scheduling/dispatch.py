from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.exceptions import (
    TASK_SCHEDULE_CASE_REQUIRED,
    TaskCenterError,
)
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.models import Tasks
from src.apps.task_center.services.execution.add_tasks import AddTasks
from src.apps.task_center.services.scheduling.fire import ScheduleFireService
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.exceptions import TEST_ENVIRONMENT_INVALID
from src.common.exceptions import MangoServerError
from src.common.logging import log


class ScheduleDispatchService:
    DISPATCH_LEASE_SECONDS = 30 * 60
    MAX_STALE_RECOVERIES = 3

    @staticmethod
    def valid_task_details(task: Tasks, *, test_env: int | None = None):
        return TaskCaseBindingService.executable_details(task, test_env=test_env)

    @classmethod
    def ensure_task_has_cases(cls, task: Tasks | None) -> None:
        if task is None or not task.pk:
            raise TaskCenterError(TASK_SCHEDULE_CASE_REQUIRED)
        for test_env in ScheduledTaskCaseSelectionService.task_test_envs(task):
            if task.execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
                has_cases = cls.valid_task_details(task, test_env=test_env).exists()
            else:
                has_cases = bool(
                    ScheduledTaskCaseSelectionService.select_task(task, test_env=test_env)
                )
            if not has_cases:
                raise TaskCenterError(TASK_SCHEDULE_CASE_REQUIRED)

    @staticmethod
    def resolve_test_env(value, default: int) -> int:
        if value is None or value == '':
            return default
        if isinstance(value, (bool, float)):
            raise TaskCenterError(TEST_ENVIRONMENT_INVALID)
        try:
            test_env = int(value)
        except (TypeError, ValueError) as error:
            raise TaskCenterError(TEST_ENVIRONMENT_INVALID, error=str(error)) from error
        if test_env not in EnvironmentEnum.get_key_list():
            raise TaskCenterError(TEST_ENVIRONMENT_INVALID)
        return test_env

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
    def recover_stale_dispatching_fires(cls, node_name: str | None = None) -> dict:
        """恢复因 scheduler-service 退出而遗留的普通测试任务分发记录。"""
        now = timezone.now()
        cutoff_time = now - timedelta(seconds=cls.DISPATCH_LEASE_SECONDS)
        stale_fires = list(
            ScheduleFire.objects.filter(
                status=ScheduleFireStatusEnum.DISPATCHING.value,
                source_type=ScheduleFireSourceTypeEnum.TEST_SUITE.value,
                update_time__lt=cutoff_time,
            ).order_by('planned_at', 'id')
        )
        recovered_count = 0
        dispatched_count = 0
        failed_count = 0
        for fire in stale_fires:
            if fire.test_suite_id:
                updated = ScheduleFire.objects.filter(
                    id=fire.id,
                    status=ScheduleFireStatusEnum.DISPATCHING.value,
                    update_time__lt=cutoff_time,
                ).update(
                    status=ScheduleFireStatusEnum.DISPATCHED.value,
                    dispatcher_node=node_name,
                    error_message=None,
                    update_time=now,
                )
                dispatched_count += updated
                continue

            extra_data = fire.extra_data if isinstance(fire.extra_data, dict) else {}
            extra_data = dict(extra_data)
            recovery_count = int(extra_data.get('dispatch_recovery_count') or 0) + 1
            extra_data['dispatch_recovery_count'] = recovery_count
            extra_data['last_recovered_at'] = now.isoformat()
            retry_exhausted = recovery_count > cls.MAX_STALE_RECOVERIES
            updated = ScheduleFire.objects.filter(
                id=fire.id,
                status=ScheduleFireStatusEnum.DISPATCHING.value,
                update_time__lt=cutoff_time,
            ).update(
                status=(
                    ScheduleFireStatusEnum.FAIL.value
                    if retry_exhausted
                    else ScheduleFireStatusEnum.PENDING.value
                ),
                dispatcher_node=None if not retry_exhausted else node_name,
                error_message=(
                    f'触发记录分发超时，自动恢复次数已超过{cls.MAX_STALE_RECOVERIES}次'
                    if retry_exhausted
                    else f'触发记录分发超时，已自动恢复为待分发（第{recovery_count}次）'
                ),
                extra_data=extra_data,
                update_time=now,
            )
            if retry_exhausted:
                failed_count += updated
            else:
                recovered_count += updated
        if recovered_count or dispatched_count or failed_count:
            log.system.warning(
                'scheduler-service 已恢复超时触发记录：'
                f'pending={recovered_count}, dispatched={dispatched_count}, '
                f'failed={failed_count}, node={node_name}'
            )
        return {
            'recovered_count': recovered_count,
            'dispatched_count': dispatched_count,
            'failed_count': failed_count,
        }

    @classmethod
    def dispatch_fire(cls, fire: ScheduleFire, node_name: str | None = None) -> int | None:
        # 手动触发和调度消费者可能拿到同一记录。锁内重新读取，生成测试套与
        # 保存关联必须一次提交，不能使用调用方持有的旧状态重复分发。
        with transaction.atomic():
            fire = ScheduleFire.objects.select_for_update().filter(id=fire.id).first()
            if fire is None:
                return None
            if fire.test_suite_id:
                return fire.test_suite_id
            if fire.status not in (
                    ScheduleFireStatusEnum.PENDING.value,
                    ScheduleFireStatusEnum.DISPATCHING.value,
            ):
                return None
            return cls._dispatch_locked_fire(fire, node_name)

    @classmethod
    def _dispatch_locked_fire(cls, fire: ScheduleFire, node_name: str | None) -> int | None:
        if fire.source_type != ScheduleFireSourceTypeEnum.TEST_SUITE.value:
            ScheduleFire.objects.filter(id=fire.id).update(
                status=ScheduleFireStatusEnum.SKIPPED.value,
                error_message='当前分发器只处理测试套定时触发',
                update_time=timezone.now(),
            )
            return None
        if not fire.task_id:
            ScheduleFireService.mark_failed(fire.id, '触发记录缺少 task_id', node_name)
            return None
        try:
            # 失败只回滚生成过程，外层仍持有触发记录锁，避免其他分发者抢先
            # 成功后又被本次失败状态覆盖。
            with transaction.atomic():
                task = Tasks.objects.select_related('project_product', 'case_people').get(id=fire.task_id)
                fire_data = fire.extra_data if isinstance(fire.extra_data, dict) else {}
                test_env = cls.resolve_test_env(
                    fire_data.get('test_env'),
                    ScheduledTaskCaseSelectionService.task_test_envs(task)[0],
                )
                test_suite_id = cls.create_test_suite(task, test_env=test_env)
                ScheduleFire.objects.filter(id=fire.id).update(
                    status=ScheduleFireStatusEnum.DISPATCHED.value,
                    test_suite_id=test_suite_id,
                    dispatcher_node=node_name,
                    update_time=timezone.now(),
                )
                return test_suite_id
        except MangoServerError as error:
            log.system.warning(f'定时触发因业务校验未通过而跳过：fire_id={fire.id}, error={error}')
            ScheduleFireService.mark_skipped(fire.id, str(error), node_name)
            return None
        except Exception as error:
            log.system.error(f'分发触发记录失败：fire_id={fire.id}, error={error}')
            ScheduleFireService.mark_failed(fire.id, str(error), node_name)
            return None

    @classmethod
    @transaction.atomic
    def create_test_suite(
            cls,
            task: Tasks,
            api_concurrency_limit: int | None = None,
            user_id: int | None = None,
            test_env: int | None = None,
            allow_unconfigured_test_env: bool = False,
    ) -> int:
        resolved_limit = (
            ApiConcurrencyService.resolve_task_trigger_limit(task.api_concurrency_limit)
            if api_concurrency_limit is None
            else api_concurrency_limit
        )
        task_test_envs = ScheduledTaskCaseSelectionService.task_test_envs(task)
        resolved_test_env = cls.resolve_test_env(test_env, task_test_envs[0])
        is_temporary_test_env = resolved_test_env not in task_test_envs
        if is_temporary_test_env and not allow_unconfigured_test_env:
            raise TaskCenterError(TEST_ENVIRONMENT_INVALID)
        if task.execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
            details = list(TaskCaseBindingService.executable_details(task, test_env=resolved_test_env))
            selected_cases = []
        else:
            details = []
            # 临时环境只改变实际执行目标，规则任务仍按原定时任务环境匹配 Case。
            if is_temporary_test_env:
                selected_cases = ScheduledTaskCaseSelectionService.select_task(task)
            else:
                selected_cases = ScheduledTaskCaseSelectionService.select_task(
                    task,
                    test_env=resolved_test_env,
                )
        if not details and not selected_cases:
            raise TaskCenterError(TASK_SCHEDULE_CASE_REQUIRED)
        report_execution_scenes = ScheduledTaskCaseSelectionService.task_execution_scenes(task)
        if (
                task.execution_scope != AutomationExecutionScopeEnum.MANUAL.value
                and not is_temporary_test_env
        ):
            report_execution_scenes = (
                ScheduledTaskCaseSelectionService.execution_scenes_for_environment(
                    report_execution_scenes,
                    resolved_test_env,
                )
            )
        add_tasks = AddTasks(
            project_product=task.project_product_id,
            test_env=resolved_test_env,
            is_notice=task.is_notice,
            user_id=user_id or task.case_people_id,
            tasks_id=task.id,
            module_id=task.module_id,
            api_concurrency_limit=resolved_limit,
            execution_scenes=report_execution_scenes,
            execution_scope=task.execution_scope,
        )
        for detail in details:
            log.system.debug(f'分发定时任务详情：task_detail_id={detail.id}')
            if detail.type == TestCaseTypeEnum.API.value and detail.api_case_id:
                selection = ApiCaseTaskBindingService.resolve_execution_selection(
                    detail.api_case_id,
                    detail.version_policy,
                )
                add_tasks.add_test_suite_details(
                    detail.api_case_id,
                    TestCaseTypeEnum.API,
                    api_case_revision_id=selection.case_revision_id if selection else None,
                    api_case_release_id=selection.case_release_id if selection else None,
                    bound_checksum=selection.checksum if selection else None,
                )
            elif detail.type == TestCaseTypeEnum.UI.value and detail.ui_case_id:
                add_tasks.add_test_suite_details(detail.ui_case_id, TestCaseTypeEnum.UI)
            elif detail.pytest_case_id:
                add_tasks.add_test_suite_details(detail.pytest_case_id, TestCaseTypeEnum.PYTEST)
        for item in selected_cases:
            if item.case_type == TestCaseTypeEnum.API.value:
                selection = ApiCaseTaskBindingService.resolve_execution_selection(item.case_id, None)
                add_tasks.add_test_suite_details(
                    item.case_id,
                    TestCaseTypeEnum.API,
                    api_case_revision_id=selection.case_revision_id,
                    api_case_release_id=selection.case_release_id,
                    bound_checksum=selection.checksum,
                )
            elif item.case_type == TestCaseTypeEnum.UI.value:
                add_tasks.add_test_suite_details(item.case_id, TestCaseTypeEnum.UI)
            elif item.case_type == TestCaseTypeEnum.PYTEST.value:
                add_tasks.add_test_suite_details(item.case_id, TestCaseTypeEnum.PYTEST)
        return add_tasks.test_suite_id

    @classmethod
    @transaction.atomic
    def create_test_suites(
            cls,
            task: Tasks,
            api_concurrency_limit: int | None = None,
            user_id: int | None = None,
            test_envs=None,
            allow_unconfigured_test_env: bool = False,
    ) -> list[int]:
        environments = ScheduledTaskCaseSelectionService.normalize_test_envs(
            test_envs if test_envs is not None else task.test_envs
        )
        return [
            cls.create_test_suite(
                task,
                api_concurrency_limit=api_concurrency_limit,
                user_id=user_id,
                test_env=test_env,
                allow_unconfigured_test_env=allow_unconfigured_test_env,
            )
            for test_env in environments
        ]
