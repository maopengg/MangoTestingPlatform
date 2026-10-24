from __future__ import annotations

from django.db import transaction

from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)

MAX_PAGE_SIZE = 100
MAX_DETAIL_CASES = 100
MAX_RECENT_FIRES = 10

from .helpers import (
    _scheduled_task_queryset_for_user,
)


def register_scheduled_task_trigger_tools(mcp):
    @mcp.tool()
    def preview_trigger_scheduled_task_impact(
            scheduled_task_id: int,
            api_concurrency_limit: int | None = None,
            test_envs: list[int] | None = None,
    ) -> dict:
        """预览手动触发定时任务的影响。

        默认按照任务配置的全部测试环境分别创建测试报告。传入 test_envs 时，
        仅本次改用指定环境执行，不修改定时任务配置；支持传入任务未配置的临时环境。
        api_concurrency_limit 可不传；不传时使用任务配置，任务也未配置时使用平台容量。
        传入值仅对本次报告生效，不会修改定时任务配置。
        """
        task = _scheduled_task_queryset_for_user().filter(id=scheduled_task_id).first()
        if not task:
            return fail("定时任务不存在或当前用户无权触发。", "SCHEDULED_TASK_NOT_FOUND")
        try:
            resolved_limit = ApiConcurrencyService.resolve_task_trigger_limit(
                task.api_concurrency_limit,
                override=api_concurrency_limit,
                override_provided=api_concurrency_limit is not None,
                error_cls=TaskCenterError,
            )
        except TaskCenterError as error:
            return fail(error.msg, "API_CONCURRENCY_INVALID")
        configured_test_envs = ScheduledTaskCaseSelectionService.task_test_envs(task)
        try:
            resolved_test_envs = (
                ScheduledTaskCaseSelectionService.normalize_test_envs(test_envs)
                if test_envs is not None
                else configured_test_envs
            )
        except TaskCenterError as error:
            return fail(error.msg, "TEST_ENV_INVALID")
        target_id = (
            f"{scheduled_task_id}:test_envs={','.join(map(str, resolved_test_envs))}:api_concurrency={resolved_limit}"
        )
        confirm_text = f"TRIGGER_SCHEDULED_TASK:{target_id}"
        impact = {
            "scheduled_task_id": scheduled_task_id,
            "task_name": task.name,
            "configured_test_envs": configured_test_envs,
            "requested_test_envs": test_envs,
            "resolved_test_envs": resolved_test_envs,
            "temporary_test_env_override": test_envs is not None,
            "configured_api_concurrency_limit": task.api_concurrency_limit,
            "requested_api_concurrency_limit": api_concurrency_limit,
            "resolved_api_concurrency_limit": resolved_limit,
            "api_platform_limit": ApiConcurrencyService.platform_limit(),
            "risk": "确认后会按本次指定的每个环境分别创建测试报告并执行；临时环境和本次并发均不会回写定时任务配置。",
        }
        return ok(
            create_dangerous_action_preview(
                "trigger_scheduled_task",
                target_id,
                confirm_text,
                impact,
            ),
            "已生成定时任务手动触发预览，请二次确认后执行",
        )

    @mcp.tool()
    def trigger_scheduled_task(
            scheduled_task_id: int,
            api_concurrency_limit: int | None = None,
            preview_token: str | None = None,
            confirm_text: str | None = None,
            test_envs: list[int] | None = None,
    ) -> dict:
        """手动触发定时任务并创建测试报告。

        必须先调用 preview_trigger_scheduled_task_impact。api_concurrency_limit
        可选，仅覆盖本次报告。test_envs 不传时使用任务配置的全部环境；
        传入时仅本次使用指定环境，不修改任务配置。
        """
        task = _scheduled_task_queryset_for_user().filter(id=scheduled_task_id).first()
        if not task:
            return fail("定时任务不存在或当前用户无权触发。", "SCHEDULED_TASK_NOT_FOUND")
        try:
            resolved_limit = ApiConcurrencyService.resolve_task_trigger_limit(
                task.api_concurrency_limit,
                override=api_concurrency_limit,
                override_provided=api_concurrency_limit is not None,
                error_cls=TaskCenterError,
            )
        except TaskCenterError as error:
            return fail(error.msg, "API_CONCURRENCY_INVALID")
        configured_test_envs = ScheduledTaskCaseSelectionService.task_test_envs(task)
        try:
            resolved_test_envs = (
                ScheduledTaskCaseSelectionService.normalize_test_envs(test_envs)
                if test_envs is not None
                else configured_test_envs
            )
        except TaskCenterError as error:
            return fail(error.msg, "TEST_ENV_INVALID")
        target_id = (
            f"{scheduled_task_id}:test_envs={','.join(map(str, resolved_test_envs))}:api_concurrency={resolved_limit}"
        )
        confirm_error = validate_dangerous_action_confirmation(
            "trigger_scheduled_task",
            target_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        user = current_user()
        with transaction.atomic():
            test_suite_ids = ScheduleDispatchService.create_test_suites(
                task,
                api_concurrency_limit=resolved_limit,
                user_id=user.id,
                test_envs=resolved_test_envs,
                allow_unconfigured_test_env=test_envs is not None,
            )
        return ok(
            {
                "scheduled_task_id": scheduled_task_id,
                "test_suite_id": test_suite_ids[0],
                "test_suite_ids": test_suite_ids,
                "test_envs": resolved_test_envs,
                "configured_test_envs": configured_test_envs,
                "temporary_test_env_override": test_envs is not None,
                "api_concurrency_limit": resolved_limit,
                "task_config_unchanged": True,
                "result_query_tool": "get_test_report_detail",
            },
            "定时任务已手动触发",
        )
