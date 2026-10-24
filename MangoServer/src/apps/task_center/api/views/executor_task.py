from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.task_center.exceptions import (
    EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID,
    TaskCenterError,
)
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.common.decorators.error_response import error_response
from src.common.responses import RESPONSE_MSG_0266, RESPONSE_MSG_0267, ResponseData


class ExecutorTaskViews(ViewSet):
    action_permission_map = {
        # 任务可能来自 UI、API、Pytest 或配置管理，不能绑定某一个业务菜单权限。
        # 接口仍要求登录，且 Service 会严格校验任务创建人。
        "get_detail": "index.home",
        "active": "index.home",
        "cancel": "index.home",
    }

    @staticmethod
    def _user_id(request: Request) -> int:
        user_id = request.user.get("id") if isinstance(request.user, dict) else getattr(request.user, "id", None)
        if not user_id:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)
        return int(user_id)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def get_detail(self, request: Request):
        task_id = request.query_params.get("task_id") or request.query_params.get("id")
        if not task_id:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)
        task = ExecutorTaskService.get_for_user(int(task_id), self._user_id(request))
        return ResponseData.success(RESPONSE_MSG_0266, ExecutorTaskService.serialize(task))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def active(self, request: Request):
        business_id = request.query_params.get("business_id")
        try:
            normalized_business_id = int(business_id) if business_id not in (None, "") else None
        except (TypeError, ValueError) as error:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID, error=str(error)) from error
        tasks = ExecutorTaskService.list_active_for_user(
            self._user_id(request),
            business_type=request.query_params.get("business_type"),
            business_id=normalized_business_id,
        )
        data = [ExecutorTaskService.serialize(task) for task in tasks]
        return ResponseData.success(RESPONSE_MSG_0266, data, len(data))

    @action(methods=["post"], detail=False)
    @error_response("system")
    def cancel(self, request: Request):
        task_id = request.data.get("task_id") or request.data.get("id")
        if not task_id:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)
        task = ExecutorTaskService.cancel(int(task_id), self._user_id(request))
        return ResponseData.success(RESPONSE_MSG_0267, ExecutorTaskService.serialize(task))
