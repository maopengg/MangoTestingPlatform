# -*- coding: utf-8 -*-
from mangotools.contracts import (
    ActuatorSystemErrorContract,
    ExecutorTaskClaimContract,
    ExecutorTaskDrainingContract,
    ExecutorTaskHeartbeatContract,
    ExecutorTaskProgressContract,
    ExecutorTaskProgressRequestContract,
    ExecutorTaskResultContract,
)

from src.network.http.apis.base import ApiError, BaseApi


class ActuatorTaskApi(BaseApi):

    @staticmethod
    def _require_success(response) -> dict:
        """任务协议必须同时校验 HTTP 状态和平台业务码。"""
        if not isinstance(response, dict):
            raise ApiError('执行器任务接口返回格式错误')
        code = response.get('code')
        if code != 200:
            raise ApiError(
                str(response.get('msg') or '执行器任务接口处理失败'),
                status_code=int(code) if isinstance(code, int) else None,
            )
        return response

    async def pull(self,
                   message_id: str,
                   task_type: str,
                   capacity: int,
                   local_queue_size: int,
                   max_queue_size: int):
        """领取测试套件任务；与统一执行器命令任务是两条独立队列。"""
        resp = await self.client.post(
            'actuator/tasks/pull',
            json={
                'message_id': message_id,
                'task_type': task_type,
                'capacity': capacity,
                'local_queue_size': local_queue_size,
                'max_queue_size': max_queue_size,
            },
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def pytest_git_credentials(
            self,
            credential_ref: str,
            repository_id: int,
            dispatch_id: str):
        resp = await self.client.post(
            'actuator/tasks/pytest-git-credentials',
            json={
                'credential_ref': credential_ref,
                'repository_id': repository_id,
                'dispatch_id': dispatch_id,
            },
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def ack(self, message_id: str, items: list[dict]):
        resp = await self.client.post(
            'actuator/tasks/ack',
            json={
                'message_id': message_id,
                'items': items,
            },
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def claim(self,
                    capacity: int = 1,
                    connection_id: str | None = None,
                    supported_task_types: list[str] | None = None,
                    protocol_versions: dict[str, int] | None = None,
                    capability_capacities: dict[str, int] | None = None,
                    task_type_capacities: dict[str, int] | None = None):
        resp = await self.client.post(
            'actuator/tasks/claim',
            json=ExecutorTaskClaimContract(
                capacity=capacity,
                connection_id=connection_id,
                supported_task_types=supported_task_types or [],
                protocol_versions=protocol_versions or {'*': 1},
                capability_capacities=capability_capacities or {},
                task_type_capacities=task_type_capacities or {},
            ).model_dump(mode='json'),
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def draining(self, draining: bool, connection_id: str | None = None):
        resp = await self.client.post(
            'actuator/tasks/draining',
            json=ExecutorTaskDrainingContract(
                connection_id=connection_id,
                draining=draining,
            ).model_dump(mode='json'),
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def running(self, task_id: int, connection_id: str | None = None):
        resp = await self.client.post(
            f'actuator/tasks/{task_id}/running',
            json=ExecutorTaskHeartbeatContract(connection_id=connection_id).model_dump(mode='json'),
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def heartbeat(self, task_id: int, connection_id: str | None = None):
        resp = await self.client.post(
            f'actuator/tasks/{task_id}/heartbeat',
            json=ExecutorTaskHeartbeatContract(connection_id=connection_id).model_dump(mode='json'),
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def progress(self, task_id: int, progress: dict, connection_id: str | None = None):
        resp = await self.client.post(
            f'actuator/tasks/{task_id}/progress',
            json=ExecutorTaskProgressRequestContract(
                connection_id=connection_id,
                progress=ExecutorTaskProgressContract.model_validate(progress),
            ).model_dump(mode='json'),
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def result(self,
                     task_id: int,
                     success: bool,
                     result_data: dict | list | None = None,
                     error_code: str | None = None,
                     error_message: str | None = None,
                     connection_id: str | None = None,
                     attempt: int = 0):
        resp = await self.client.post(
            f'actuator/tasks/{task_id}/result',
            json=ExecutorTaskResultContract(
                connection_id=connection_id,
                attempt=attempt,
                success=success,
                result_data=result_data,
                error_code=error_code,
                error_message=error_message,
            ).model_dump(mode='json'),
            headers=self._headers(),
        )
        return self._require_success(resp)

    async def report_system_error(
            self,
            operation: str,
            exception_type: str,
            message: str,
            traceback_text: str | None = None):
        resp = await self.client.post(
            'actuator/tasks/system-errors',
            json=ActuatorSystemErrorContract(
                operation=operation,
                exception_type=exception_type,
                message=message,
                traceback=traceback_text,
            ).model_dump(mode='json'),
            headers=self._headers(),
            timeout=5,
        )
        return self._require_success(resp)
