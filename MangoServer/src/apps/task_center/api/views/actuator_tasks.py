from mangotools.contracts import (
    ActuatorSystemErrorContract,
    ExecutorTaskClaimContract,
    ExecutorTaskDrainingContract,
    ExecutorTaskHeartbeatContract,
    ExecutorTaskProgressRequestContract,
    ExecutorTaskResultContract,
    TaskPullRequest,
)
from pydantic import ValidationError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_pytest.services.repository.git_credentials import PytestGitCredentialService
from src.apps.auto_pytest.services.execution.cases.case_flow import PyCaseFlow
from src.apps.auto_ui.services.execution.cases.case_flow import UiCaseFlow
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.services.runtime_center.system_error_event import (
    SystemErrorEventService,
    SystemErrorEventSource,
)
from src.apps.task_center.exceptions import (
    EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID,
    TaskCenterError,
)
from src.apps.task_center.services.execution.actuator_task_lease import ActuatorTaskLease
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.common.decorators.error_response import error_response
from src.common.logging import log
from src.common.responses import (
    RESPONSE_MSG_0268,
    RESPONSE_MSG_0269,
    RESPONSE_MSG_0271,
    RESPONSE_MSG_0308,
    RESPONSE_MSG_0309,
    RESPONSE_MSG_0310,
    RESPONSE_MSG_0311,
    ResponseData,
)


class ActuatorTaskViews(ViewSet):
    """执行器统一任务协议；任务领取与结果提交均以数据库状态为准。"""

    @staticmethod
    def _actuator_username(request: Request) -> str:
        user = request.user
        client_type = user.get("client_type") if isinstance(user, dict) else None
        username = user.get("username") if isinstance(user, dict) else getattr(user, "username", None)
        if client_type != ClientTypeEnum.ACTUATOR.value or not username:
            raise AuthenticationFailed("当前登录凭据不是执行器凭据，请重新登录执行器")
        return str(username)

    @staticmethod
    def _model(model_class, data):
        try:
            return model_class.model_validate(data or {})
        except ValidationError as error:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID, error=str(error)) from error

    @error_response("system")
    def pytest_git_credentials(self, request: Request):
        """获取执行器任务所需的 Pytest 仓库凭据"""
        username = self._actuator_username(request)
        reference = str((request.data or {}).get("credential_ref") or "").strip()
        try:
            repository_id = int((request.data or {}).get("repository_id"))
        except (TypeError, ValueError):
            repository_id = None
        dispatch_id = str((request.data or {}).get("dispatch_id") or "").strip() or None
        credentials = PytestGitCredentialService.resolve(
            reference,
            username,
            repository_id=repository_id,
            dispatch_id=dispatch_id,
        )
        return ResponseData.success(RESPONSE_MSG_0309, credentials)

    @error_response("system")
    def pull(self, request: Request):
        """保留测试套件原有领取协议，避免与执行器命令任务混为一谈。"""
        data = request.data or {}
        username = self._actuator_username(request)
        task_type = data.get("task_type")
        capacity = int(data.get("capacity") or 0)
        message_id = data.get("message_id")
        if task_type in ("ui", TestCaseTypeEnum.UI.value):
            task_type = TestCaseTypeEnum.UI
        elif task_type in ("pytest", TestCaseTypeEnum.PYTEST.value):
            task_type = TestCaseTypeEnum.PYTEST
        else:
            return ResponseData.fail(RESPONSE_MSG_0310, data={"tasks": []})
        if capacity <= 0:
            return ResponseData.fail(RESPONSE_MSG_0310, data={"tasks": []})

        get_task = TaskPullRequest(type=task_type, username=username)
        if task_type == TestCaseTypeEnum.UI:
            tasks = UiCaseFlow.pull_cases(get_task, capacity, message_id)
        else:
            tasks = PyCaseFlow.pull_cases(get_task, capacity, message_id)
        return ResponseData.success(RESPONSE_MSG_0308, data={
            "message_id": message_id,
            "tasks": tasks,
        })

    @error_response("system")
    def ack(self, request: Request):
        """确认执行器任务接收"""
        data = request.data or {}
        username = self._actuator_username(request)
        message_id = data.get("message_id")
        items = data.get("items") or []
        if not message_id or not isinstance(items, list):
            return ResponseData.fail(RESPONSE_MSG_0310, data={"items": []})
        rejected = [item for item in items if item.get("status") == "rejected"]
        if rejected:
            log.system.warning(f"执行器任务确认包含拒绝项：{rejected[:5]}")
        accepted_count, rejected_count = ActuatorTaskLease.ack_items(items, username, message_id)
        return ResponseData.success(RESPONSE_MSG_0309, data={
            "message_id": message_id,
            "accepted": accepted_count,
            "rejected": rejected_count,
        })

    @error_response("system")
    def claim(self, request: Request):
        """领取执行器任务"""
        username = self._actuator_username(request)
        model = self._model(ExecutorTaskClaimContract, request.data)
        tasks = ExecutorTaskService.claim(
            connection_id=model.connection_id,
            username=username,
            capacity=model.capacity,
            supported_task_types=model.supported_task_types,
            protocol_versions=model.protocol_versions,
            capability_capacities=model.capability_capacities,
            task_type_capacities=model.task_type_capacities,
        )
        return ResponseData.success(RESPONSE_MSG_0268, {
            "tasks": [ExecutorTaskService.claim_payload(task) for task in tasks],
        })

    @error_response("system")
    def draining(self, request: Request):
        """设置执行器任务排空状态"""
        username = self._actuator_username(request)
        model = self._model(ExecutorTaskDrainingContract, request.data)
        connection = ExecutorTaskService.set_connection_draining(
            connection_id=model.connection_id,
            username=username,
            draining=model.draining,
        )
        return ResponseData.success(RESPONSE_MSG_0269, {
            "connection_id": str(connection.connection_id),
            "draining": model.draining,
        })

    @error_response("system")
    def running(self, request: Request, task_id: int):
        """上报执行器任务开始运行"""
        username = self._actuator_username(request)
        model = self._model(ExecutorTaskHeartbeatContract, request.data)
        task = ExecutorTaskService.mark_running(task_id, model.connection_id, username)
        return ResponseData.success(RESPONSE_MSG_0269, ExecutorTaskService.serialize(task))

    @error_response("system")
    def heartbeat(self, request: Request, task_id: int):
        """上报执行器任务心跳"""
        username = self._actuator_username(request)
        model = self._model(ExecutorTaskHeartbeatContract, request.data)
        task = ExecutorTaskService.heartbeat(task_id, model.connection_id, username)
        return ResponseData.success(RESPONSE_MSG_0269, {
            **ExecutorTaskService.serialize(task),
            "cancel_requested": task.cancel_requested_at is not None,
        })

    @error_response("system")
    def progress(self, request: Request, task_id: int):
        """上报执行器任务执行进度"""
        username = self._actuator_username(request)
        model = self._model(ExecutorTaskProgressRequestContract, request.data)
        task = ExecutorTaskService.update_progress(
            task_id,
            model.connection_id,
            username,
            model.progress,
        )
        return ResponseData.success(RESPONSE_MSG_0311, ExecutorTaskService.serialize(task))

    @error_response("system")
    def result(self, request: Request, task_id: int):
        """上报执行器任务执行结果"""
        username = self._actuator_username(request)
        model = self._model(ExecutorTaskResultContract, request.data)
        task = ExecutorTaskService.complete(
            task_id=task_id,
            connection_id=model.connection_id,
            username=username,
            attempt=model.attempt,
            success=model.success,
            result_data=model.result_data,
            error_code=model.error_code,
            error_message=model.error_message,
        )
        return ResponseData.success(RESPONSE_MSG_0271, ExecutorTaskService.serialize(task))

    @error_response("system")
    def report_system_error(self, request: Request):
        """接收执行器进程的非预期系统异常；业务失败仍通过任务结果协议上报。"""
        username = self._actuator_username(request)
        model = self._model(ActuatorSystemErrorContract, request.data)
        SystemErrorEventService.record(
            service_name=f'actuator:{username}'[:64],
            source=SystemErrorEventSource.ACTUATOR,
            request_path=model.operation,
            exception_type=model.exception_type,
            message=model.message,
            trace=model.traceback,
        )
        return ResponseData.success(RESPONSE_MSG_0309)
