from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from pydantic import BaseModel

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import (
    ExecutorModeEnum,
    ExecutorTaskStatusEnum,
    ExecutorTaskTypeEnum,
)
from src.apps.system.enums import ServerApiCommandEnum, ServerPytestCommandEnum, ServerToolsCommandEnum, \
    ServerUiCommandEnum
from src.apps.system.exceptions import SystemError
from src.apps.system.services.system_config import SystemConfigService
from src.apps.task_center.exceptions import EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.user.models import User


class SocketMessageService:
    """统一创建执行器任务；函数名只用于执行器侧分发，不承担可靠消息语义。"""

    FUNCTION_TASK_TYPES = {
        ServerUiCommandEnum.ELEMENT_CHECK.value: ExecutorTaskTypeEnum.ELEMENT_CHECK.value,
        ServerUiCommandEnum.OPEN_TARGET_PAGE.value: ExecutorTaskTypeEnum.PAGE_OPEN.value,
        ServerUiCommandEnum.PAGE_STEPS.value: ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value,
        ServerUiCommandEnum.CASE_BATCH.value: ExecutorTaskTypeEnum.UI_CASE.value,
        ServerUiCommandEnum.AUTH_AUTO_CAPTURE.value: ExecutorTaskTypeEnum.AUTH_CAPTURE.value,
        ServerUiCommandEnum.RECORDING.value: ExecutorTaskTypeEnum.RECORDING.value,
        ServerUiCommandEnum.NEW_PAGE_OBJ.value: ExecutorTaskTypeEnum.PAGE_OPEN.value,
        ServerUiCommandEnum.AUTH_AUTO.value: ExecutorTaskTypeEnum.AUTH_START.value,
        ServerUiCommandEnum.LIVE_STREAM_START.value: ExecutorTaskTypeEnum.LIVE_CONTROL.value,
        ServerUiCommandEnum.LIVE_STREAM_STOP.value: ExecutorTaskTypeEnum.LIVE_CONTROL.value,
        ServerUiCommandEnum.LIVE_WORKSPACE_START.value: ExecutorTaskTypeEnum.LIVE_CONTROL.value,
        ServerUiCommandEnum.LIVE_WORKSPACE_STOP.value: ExecutorTaskTypeEnum.LIVE_CONTROL.value,
        ServerUiCommandEnum.PAGE_SCAN.value: ExecutorTaskTypeEnum.PAGE_SCAN.value,
        ServerUiCommandEnum.SET_OPEN_STATUS.value: ExecutorTaskTypeEnum.CONFIG_COMMAND.value,
        ServerUiCommandEnum.SET_DEBUG.value: ExecutorTaskTypeEnum.CONFIG_COMMAND.value,
        ServerToolsCommandEnum.REFRESH_METHOD_OPTIONS.value: ExecutorTaskTypeEnum.CONFIG_COMMAND.value,
        ServerToolsCommandEnum.GET_ACTUATOR_CONFIG.value: ExecutorTaskTypeEnum.CONFIG_COMMAND.value,
        ServerToolsCommandEnum.UPDATE_ACTUATOR_CONFIG.value: ExecutorTaskTypeEnum.CONFIG_COMMAND.value,
        ServerToolsCommandEnum.TASK_AVAILABLE.value: ExecutorTaskTypeEnum.TEST_CONTROL.value,
        ServerToolsCommandEnum.STOP_TEST_SUITE.value: ExecutorTaskTypeEnum.TEST_CONTROL.value,
        ServerApiCommandEnum.API_INFO.value: ExecutorTaskTypeEnum.API_EXECUTION.value,
        ServerApiCommandEnum.API_CASE.value: ExecutorTaskTypeEnum.API_EXECUTION.value,
        ServerPytestCommandEnum.TEST_CASE.value: ExecutorTaskTypeEnum.PYTEST_EXECUTION.value,
    }

    @classmethod
    def send_socket_data(
            cls,
            socket_data: SocketEnvelopeContract,
            *,
            message_key: str | None = None,
            ttl_seconds: int | None = None,
            executor_mode: str = ExecutorModeEnum.SPECIFIED.value,
            execution_timeout_seconds: int | None = None,
            created_by: User | int | str | None = None,
            target_executor_connection=None,
            **_,
    ):
        if socket_data.is_notice == ClientTypeEnum.WEB.value:
            cls._push_notification(socket_data, ClientTypeEnum.WEB.value)
            return None
        if socket_data.is_notice != ClientTypeEnum.ACTUATOR.value or not socket_data.data:
            raise SystemError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)
        func_name = socket_data.data.func_name
        func_args = cls._json_value(socket_data.data.func_args)
        if func_name == ServerToolsCommandEnum.TASK_AVAILABLE.value:
            # 任务可领取只是一次轻量唤醒，不再反向创建另一条任务记录。
            cls._push_notification(socket_data, ClientTypeEnum.ACTUATOR.value)
            return None
        task_type = cls.FUNCTION_TASK_TYPES.get(func_name)
        if func_name == ServerUiCommandEnum.ELEMENT_CHECK.value and func_args.get("check_mode") == "deep":
            task_type = ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value
        if task_type is None:
            # 浏览器控制事件会持续扩展；未单独分类的命令仍进入统一任务表，
            # 由执行器按 func_name 分发，避免新增事件重新退回不可靠的直推链路。
            task_type = ExecutorTaskTypeEnum.EXECUTOR_COMMAND.value
        creator = created_by if created_by is not None else cls._creator(func_args)
        if task_type in {
            ExecutorTaskTypeEnum.ELEMENT_CHECK.value,
            ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value,
            ExecutorTaskTypeEnum.ELEMENT_COLLECT.value,
            ExecutorTaskTypeEnum.PAGE_OPEN.value,
            ExecutorTaskTypeEnum.PAGE_SCAN.value,
            ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value,
            ExecutorTaskTypeEnum.PAGE_STEP_NODE_DEBUG.value,
            ExecutorTaskTypeEnum.UI_CASE.value,
            ExecutorTaskTypeEnum.UI_CASE_STEP.value,
            ExecutorTaskTypeEnum.AUTH_START.value,
            ExecutorTaskTypeEnum.AUTH_CAPTURE.value,
            ExecutorTaskTypeEnum.RECORDING.value,
        }:
            func_args['runtime_config'] = cls._ui_runtime_config_snapshot()
        business_id = cls._business_id(func_name, func_args)
        executor_user = None if executor_mode == ExecutorModeEnum.PUBLIC.value else socket_data.user
        task = ExecutorTaskService.create(
            task_type=task_type,
            created_by=creator,
            executor_mode=executor_mode,
            executor_user=executor_user,
            payload={
                "schema_version": 1,
                "func_name": func_name,
                "func_args": func_args,
            },
            business_type=func_name,
            business_id=business_id,
            workspace_id=func_args.get("workspace_id") if isinstance(func_args, dict) else None,
            message_key=message_key or f"socket-command:{socket_data.message_id}",
            schedule_timeout_seconds=ttl_seconds,
            execution_timeout_seconds=execution_timeout_seconds,
            target_executor_connection=target_executor_connection,
        )
        cls._push_task_available(task)
        return task

    @staticmethod
    def _ui_runtime_config_snapshot() -> dict:
        fixed_seconds = SystemConfigService.get('UI_FIXED_LOCATOR_RETRY_SECONDS', default=10)
        smart_seconds = SystemConfigService.get('UI_SMART_LOCATOR_TIMEOUT_SECONDS', default=30)
        visual_enabled = SystemConfigService.get('UI_VISUAL_LOCATOR_ENABLED', default=False)
        if isinstance(visual_enabled, str):
            visual_enabled = visual_enabled.strip().lower() in {'1', 'true', 'yes', 'on'}
        return {
            'schema_version': 1,
            'fixed_locator_retry_seconds': SystemConfigService.normalize_int_range(
                fixed_seconds, default=10, min_value=0, max_value=60,
            ),
            'smart_locator_timeout_seconds': SystemConfigService.normalize_int_range(
                smart_seconds, default=30, min_value=5, max_value=120,
            ),
            'visual_locator_enabled': bool(visual_enabled),
            'visual_model_config_version': None,
            'source': 'platform_task_snapshot',
        }

    @classmethod
    def _push_task_available(cls, task) -> None:
        payload = SocketEnvelopeContract(
            code=200,
            msg="有新的执行器任务可领取",
            user=getattr(task.executor_user, "username", None),
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=SocketCommandContract(
                func_name=ServerToolsCommandEnum.TASK_AVAILABLE.value,
                func_args={
                    "task_id": task.id,
                    "task_type": task.task_type,
                },
            ),
        )
        cls._push_notification(payload, ClientTypeEnum.ACTUATOR.value)

    @classmethod
    def send_executor_task_result(cls, task_id: int) -> None:
        """向任务发起人发送易读的最终结果；任务事实仍以数据库状态为准。"""
        from src.apps.task_center.models import ExecutorTask

        task = ExecutorTask.objects.select_related("created_by").filter(id=task_id).first()
        notice = cls.build_executor_task_result_notice(task)
        if notice is None:
            return
        cls._push_notification(notice, ClientTypeEnum.WEB.value)

    @classmethod
    def build_executor_task_result_notice(cls, task) -> SocketEnvelopeContract | None:
        """构造统一任务完成通知，供 realtime-service 直接投递。"""
        if task is None or task.created_by is None:
            return None
        result = task.result_data if isinstance(task.result_data, dict) else {}
        payload = task.payload if isinstance(task.payload, dict) else {}
        func_args = payload.get("func_args") if isinstance(payload.get("func_args"), dict) else {}
        result_name = str(
            result.get("name")
            or func_args.get("name")
            or f"任务 #{task.id}"
        )
        status_text = cls._task_status_title(task.status)
        duration_seconds = None
        if task.started_at and task.finished_at:
            duration_seconds = max(0, int((task.finished_at - task.started_at).total_seconds()))
        duration_text = cls._duration_text(duration_seconds)
        error_message = cls._compact_error_message(
            task.error_message or result.get("error_message") or ""
        )
        summary = f'{cls._task_type_title(task.task_type)}《{result_name}》{status_text}'
        if duration_text:
            summary += f'，耗时 {duration_text}'
        if task.status != ExecutorTaskStatusEnum.SUCCESS.value:
            summary += f'。失败原因：{error_message or "未返回具体原因，请进入结果详情查看"}'
        else:
            summary += '。'
        return SocketEnvelopeContract(
            code=200 if task.status == ExecutorTaskStatusEnum.SUCCESS.value else 300,
            msg=summary,
            user=task.created_by.username,
            is_notice=ClientTypeEnum.WEB.value,
            data=SocketCommandContract(
                func_name="executor_task_result",
                func_args={
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "business_type": task.business_type,
                    "business_id": task.business_id,
                    "result_name": result_name,
                    "status": task.status,
                    "status_text": status_text,
                    "success": task.status == ExecutorTaskStatusEnum.SUCCESS.value,
                    "error_message": error_message,
                    "duration_seconds": duration_seconds,
                    "finished_at": ExecutorTaskService._datetime_text(task.finished_at),
                },
            ),
        )

    @staticmethod
    def _task_type_title(task_type: str) -> str:
        return {
            ExecutorTaskTypeEnum.API_EXECUTION.value: "API测试",
            ExecutorTaskTypeEnum.PYTEST_EXECUTION.value: "Pytest用例",
            ExecutorTaskTypeEnum.ELEMENT_CHECK.value: "元素检测",
            ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value: "元素深度检测",
            ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value: "UI步骤",
            ExecutorTaskTypeEnum.PAGE_STEP_NODE_DEBUG.value: "UI步骤节点",
            ExecutorTaskTypeEnum.UI_CASE.value: "UI用例",
            ExecutorTaskTypeEnum.UI_CASE_STEP.value: "UI用例步骤",
        }.get(str(task_type), "测试任务")

    @staticmethod
    def _task_status_title(status: str) -> str:
        return {
            ExecutorTaskStatusEnum.SUCCESS.value: "执行通过",
            ExecutorTaskStatusEnum.FAILED.value: "执行失败",
            ExecutorTaskStatusEnum.INTERRUPTED.value: "执行中断",
            ExecutorTaskStatusEnum.CANCELLED.value: "已取消",
            ExecutorTaskStatusEnum.TIMEOUT.value: "执行超时",
        }.get(str(status), "已结束")

    @staticmethod
    def _duration_text(duration_seconds: int | None) -> str:
        if duration_seconds is None:
            return ""
        minutes, seconds = divmod(max(0, int(duration_seconds)), 60)
        return f"{minutes}分{seconds}秒" if minutes else f"{seconds}秒"

    @staticmethod
    def _compact_error_message(error_message: Any, max_length: int = 300) -> str:
        text = " ".join(str(error_message or "").split())
        if len(text) <= max_length:
            return text
        return f"{text[:max_length].rstrip()}…"

    @staticmethod
    def _push_notification(socket_data: SocketEnvelopeContract, client_type: int) -> None:
        """发送非可靠唤醒/提示；失败不影响数据库任务事实。"""
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        group_names: list[str] = []
        if socket_data.user:
            user_id = User.objects.filter(username=socket_data.user).values_list("id", flat=True).first()
            if user_id:
                group_names.append(f"mango.realtime.user.{client_type}.{user_id}")
        elif client_type == ClientTypeEnum.ACTUATOR.value:
            group_names.append(f"mango.realtime.client.{client_type}")
        payload = socket_data.model_dump(mode="json")
        for group_name in group_names:
            try:
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {"type": "socket.notification", "payload": payload},
                )
            except Exception:
                # 轻量通知只是降低领取延迟；执行器和前端仍由 HTTP 轮询恢复。
                continue

    @staticmethod
    def _json_value(value: Any):
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value]
        raise SystemError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)

    @staticmethod
    def _creator(payload):
        if isinstance(payload, dict):
            return payload.get("send_user") or payload.get("username") or payload.get("user")
        return None

    @staticmethod
    def _business_id(func_name: str, payload) -> int | None:
        if not isinstance(payload, dict):
            return None
        if func_name == ServerUiCommandEnum.ELEMENT_CHECK.value:
            element_list = payload.get("element_list") or []
            if element_list and isinstance(element_list[0], dict):
                value = element_list[0].get("id")
                if isinstance(value, int):
                    return value
        for key in (
                "element_id",
                "page_step_id",
                "steps_id",
                "case_id",
                "config_id",
                "page_id",
                "id",
        ):
            value = payload.get(key)
            if isinstance(value, int):
                return value
        return None
