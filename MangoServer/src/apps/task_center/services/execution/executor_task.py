import json
import random
from copy import copy
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import time
import uuid
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q, F
from django.utils import timezone
from pydantic import BaseModel

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import (
    ExecutorModeEnum,
    ExecutorTaskTypeEnum,
    SocketConnectionStatusEnum,
    ExecutorTaskStatusEnum,
)
from src.apps.system.enums import ServerApiCommandEnum, ServerToolsCommandEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.task_center.enums import ExecutorTaskErrorCodeEnum
from src.apps.task_center.exceptions import (
    EXECUTOR_TASK_EXECUTOR_TASK_EXECUTION_CLEANUP_NOT_FOUND,
    EXECUTOR_TASK_EXECUTOR_TASK_EXECUTION_ACCESS_DENIED,
    EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID,
    EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID,
    EXECUTOR_TASK_EXECUTOR_TASK_RESULT_EXECUTION_INVALID,
    EXECUTOR_TASK_EXECUTOR_USER_EXECUTION_NOT_FOUND,
    TaskCenterError,
)
from src.apps.task_center.models import SocketConnection, ExecutorTask
from src.apps.task_center.signals import executor_task_finished
from src.apps.user.models import User
from src.common.exceptions import ErrorDefinition
from src.common.logging import log


@dataclass(frozen=True)
class ExecutorTaskPolicy:
    schedule_timeout_seconds: int
    execution_timeout_seconds: int
    lease_seconds: int = 45
    max_retries: int = 0


class ExecutorTaskService:
    """执行器任务的唯一状态机；WebSocket 只允许把 task_id 当作唤醒提示。"""

    MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
    MAX_RESULT_BYTES = 10 * 1024 * 1024
    MAX_ERROR_LENGTH = 2048
    DEADLOCK_MAX_ATTEMPTS = 3
    DEADLOCK_BASE_DELAY_SECONDS = 0.02
    RECOVERY_BATCH_SIZE = 200
    COMPLETION_NOTIFICATION_TASK_TYPES = {
        ExecutorTaskTypeEnum.API_EXECUTION.value,
        ExecutorTaskTypeEnum.PYTEST_EXECUTION.value,
        ExecutorTaskTypeEnum.ELEMENT_CHECK.value,
        ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value,
        ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value,
        ExecutorTaskTypeEnum.PAGE_STEP_NODE_DEBUG.value,
        ExecutorTaskTypeEnum.UI_CASE.value,
        ExecutorTaskTypeEnum.UI_CASE_STEP.value,
    }
    DEFAULT_POLICY = ExecutorTaskPolicy(30, 10 * 60)
    POLICIES = {
        ExecutorTaskTypeEnum.EXECUTOR_COMMAND.value: ExecutorTaskPolicy(15, 5 * 60),
        ExecutorTaskTypeEnum.LIVE_CONTROL.value: ExecutorTaskPolicy(10, 5 * 60),
        ExecutorTaskTypeEnum.CONFIG_COMMAND.value: ExecutorTaskPolicy(10, 60),
        ExecutorTaskTypeEnum.TEST_CONTROL.value: ExecutorTaskPolicy(10, 60),
        ExecutorTaskTypeEnum.API_EXECUTION.value: ExecutorTaskPolicy(30, 60 * 60),
        ExecutorTaskTypeEnum.PYTEST_EXECUTION.value: ExecutorTaskPolicy(30, 60 * 60),
        ExecutorTaskTypeEnum.ELEMENT_CHECK.value: ExecutorTaskPolicy(15, 5 * 60, max_retries=1),
        ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value: ExecutorTaskPolicy(15, 5 * 60, max_retries=1),
        ExecutorTaskTypeEnum.ELEMENT_COLLECT.value: ExecutorTaskPolicy(15, 2 * 60),
        ExecutorTaskTypeEnum.PAGE_SCAN.value: ExecutorTaskPolicy(15, 5 * 60, max_retries=1),
        ExecutorTaskTypeEnum.PAGE_OPEN.value: ExecutorTaskPolicy(15, 2 * 60),
        ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value: ExecutorTaskPolicy(15, 30 * 60),
        ExecutorTaskTypeEnum.PAGE_STEP_NODE_DEBUG.value: ExecutorTaskPolicy(15, 10 * 60),
        ExecutorTaskTypeEnum.UI_CASE.value: ExecutorTaskPolicy(5 * 60, 60 * 60),
        ExecutorTaskTypeEnum.UI_CASE_STEP.value: ExecutorTaskPolicy(30, 30 * 60),
        ExecutorTaskTypeEnum.AUTH_START.value: ExecutorTaskPolicy(15, 15 * 60),
        ExecutorTaskTypeEnum.AUTH_CAPTURE.value: ExecutorTaskPolicy(15, 15 * 60),
        ExecutorTaskTypeEnum.RECORDING.value: ExecutorTaskPolicy(15, 2 * 60 * 60),
        ExecutorTaskTypeEnum.PERF_EXECUTION.value: ExecutorTaskPolicy(5 * 60, 24 * 60 * 60, lease_seconds=60),
    }

    @classmethod
    @transaction.atomic
    def create_cleanup_task(cls, execution_id, *, created_by=None, owner=None, controlled_retry=False,
                            force_cleanup=True, allow_missing=True, mode=None, recovery_owner=None):
        from src.apps.data_factory.schemas.cleanup_resource import CleanupTaskPayload
        from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
        # 与历史补偿授权使用同一归属锁，避免授权落库时出现新清理持有者。
        CleanupPersistenceService.lock_execution(execution_id)
        payload = CleanupTaskPayload(execution_id=execution_id, force_cleanup=force_cleanup,
                                     allow_missing=allow_missing, **({'mode': mode} if mode is not None else {}),
                                     **({'recovery_owner': recovery_owner} if recovery_owner is not None else {}),
                                     **(owner or {})).model_dump(mode='json', exclude_none=True)
        previous = ExecutorTask.objects.select_for_update().filter(
            task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value, business_id=execution_id,
        ).order_by('-id').first()
        upgrade = (previous is not None and previous.status == ExecutorTaskStatusEnum.SUCCESS.value
                   and force_cleanup and (previous.payload or {}).get('force_cleanup') is False)
        if previous is not None and (previous.status not in ExecutorTaskStatusEnum.terminal_values()
                                     or not (controlled_retry or upgrade)):
            return previous
        retry = int(previous.retry_count) + 1 if previous is not None else 0
        task = cls.create(
            task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value, created_by=created_by,
            executor_mode=ExecutorModeEnum.PUBLIC.value, business_type='data_factory_cleanup',
            business_id=execution_id, payload=payload,
            message_key=f'data-factory-cleanup:{execution_id}:{retry}', schedule_timeout_seconds=3600,
            execution_timeout_seconds=3600,
        )
        if retry and task.retry_count != retry:
            task.retry_count = retry
            task.save(update_fields=['retry_count', 'update_time'])
        return task

    @classmethod
    def claim_cleanup_task(cls, *, observations_only=False):
        from src.apps.task_center.schemas.server_task import ServerTaskLease
        from src.apps.data_factory.enums.cleanup import DataFactoryCleanupModeEnum
        now = timezone.now()
        with transaction.atomic():
            candidates = ExecutorTask.objects.select_for_update(skip_locked=True).filter(
                task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value,
            ).filter((Q(status=ExecutorTaskStatusEnum.PENDING.value, available_at__lte=now)
                     | Q(status=ExecutorTaskStatusEnum.RUNNING.value, lease_expires_at__lte=now))
                     & (Q(payload__mode__isnull=True) | ~Q(payload__mode=DataFactoryCleanupModeEnum.SYNCHRONOUS.value)))
            if observations_only:
                candidates = candidates.filter(progress_data__sql_done=True)
            ordering = (['available_at', 'id'] if observations_only else
                        [F('progress_data__sql_done').desc(nulls_last=True), 'available_at', 'id'])
            task = candidates.order_by(*ordering).first()
            if task is None:
                return None
            recovered = task.status == ExecutorTaskStatusEnum.RUNNING.value
            progress = dict(task.progress_data) if isinstance(task.progress_data, dict) else {'invalid_snapshot': True}
            previous_generation = progress.get('generation', 0)
            if type(previous_generation) is not int or previous_generation < 0:
                # 将损坏快照交给服务端任务校验转失败，不能在领取前反复异常造成永久积压。
                progress = {'invalid_snapshot': True}
                previous_generation = 0
            generation = previous_generation + int(recovered)
            token = uuid.uuid4().hex
            task.progress_data = {**progress, 'generation': generation, 'claim_token': token}
            task.status = ExecutorTaskStatusEnum.RUNNING.value
            task.started_at = task.started_at or now
            task.lease_expires_at = now + timedelta(seconds=60)
            task.save(update_fields=['status', 'started_at', 'lease_expires_at', 'progress_data', 'update_time'])
            return ServerTaskLease(task_id=task.id, token=token, generation=generation, recovered=recovered,
                                   payload=task.payload, progress=progress)

    @classmethod
    @transaction.atomic
    def begin_inline_cleanup(cls, execution_id, *, created_by=None, controlled_retry=False,
                             force_cleanup=True, allow_missing=True):
        from src.apps.data_factory.enums.cleanup import DataFactoryCleanupModeEnum
        from src.apps.task_center.schemas.server_task import ServerTaskLease
        task = cls.create_cleanup_task(execution_id, created_by=created_by, controlled_retry=controlled_retry,
            force_cleanup=force_cleanup, allow_missing=allow_missing, mode=DataFactoryCleanupModeEnum.SYNCHRONOUS)
        task = ExecutorTask.objects.select_for_update().get(id=task.id)
        if task.status in ExecutorTaskStatusEnum.terminal_values():
            return task, None
        if (task.status != ExecutorTaskStatusEnum.PENDING.value
                or task.payload.get('mode') != DataFactoryCleanupModeEnum.SYNCHRONOUS.value):
            return task, None
        token = uuid.uuid4().hex
        task.status = ExecutorTaskStatusEnum.RUNNING.value
        task.started_at = timezone.now()
        task.lease_expires_at = task.started_at + timedelta(seconds=60)
        task.progress_data = {'generation': 0, 'claim_token': token}
        task.save(update_fields=['status', 'started_at', 'lease_expires_at', 'progress_data', 'update_time'])
        return task, ServerTaskLease(task_id=task.id, token=token, generation=0, recovered=False,
                                    payload=task.payload, progress={})

    @classmethod
    def finish_cleanup_step(cls, lease, progress, *, next_at=None, success=False, error=None, inline=False):
        now = timezone.now()
        with transaction.atomic():
            task = ExecutorTask.objects.select_for_update().get(id=lease.task_id)
            if (task.status != ExecutorTaskStatusEnum.RUNNING.value
                    or (task.progress_data or {}).get('claim_token') != lease.token
                    or not task.lease_expires_at or task.lease_expires_at <= now):
                return False
            task.progress_data = {**progress, 'generation': lease.generation, 'claim_token': lease.token}
            task.lease_expires_at = None
            if next_at is not None:
                task.status, task.available_at = (ExecutorTaskStatusEnum.RUNNING.value if inline else
                                                 ExecutorTaskStatusEnum.PENDING.value), next_at
                if inline:
                    task.lease_expires_at = now + timedelta(seconds=60)
            else:
                task.status = ExecutorTaskStatusEnum.SUCCESS.value if success else ExecutorTaskStatusEnum.FAILED.value
                task.error_message = error
                task.finished_at = now
            task.save(update_fields=['progress_data', 'lease_expires_at', 'status', 'available_at',
                                     'error_message', 'finished_at', 'update_time'])
            return True

    @classmethod
    def with_cleanup_lease(cls, lease, callback):
        with transaction.atomic():
            task = ExecutorTask.objects.select_for_update().get(id=lease.task_id)
            now = timezone.now()
            if (task.status != ExecutorTaskStatusEnum.RUNNING.value
                    or (task.progress_data or {}).get('claim_token') != lease.token
                    or not task.lease_expires_at or task.lease_expires_at <= now):
                return False, None
            # 大场景的 SQL 阶段可能超过一次领取时长；仅当前有效持有者在安全检查点续租。
            # 已过期或 token 改变仍拒绝，不能复活旧持有者或重放未知 SQL。
            if task.lease_expires_at - now <= timedelta(seconds=30):
                task.lease_expires_at = now + timedelta(seconds=60)
                task.save(update_fields=['lease_expires_at', 'update_time'])
            return True, callback()

    @classmethod
    def reconcile_verified_cleanup_task(cls, execution_id, verify):
        """调用方已锁定执行；先锁任务，再由业务回调锁明细、核验证据，不接管活跃租约。"""
        from src.apps.data_factory.schemas.cleanup_resource import CleanupTaskProgress, FactoryExecutionReconciliation
        from pydantic import ValidationError
        task = ExecutorTask.objects.select_for_update().filter(
            task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value,
            business_id=execution_id).order_by('-id').first()
        if task is not None and task.status not in (ExecutorTaskStatusEnum.SUCCESS.value, ExecutorTaskStatusEnum.FAILED.value):
            return False
        if not verify():
            return False
        if task is None or task.status == ExecutorTaskStatusEnum.SUCCESS.value:
            return True
        try:
            progress = CleanupTaskProgress.model_validate(task.progress_data or {}, strict=True)
            progress.reconciliation = FactoryExecutionReconciliation(
                checked_at=timezone.now().isoformat(), reason='all_registered_resources_verified_cleaned',
                previous_error=task.error_message or None)
        except ValidationError:
            return False
        task.progress_data = progress.model_dump(mode='json', exclude_none=True)
        task.status = ExecutorTaskStatusEnum.SUCCESS.value
        task.error_message = None
        task.lease_expires_at = None
        # finished_at 保留实际原任务结束时间；对账时间单独保存在 progress。
        task.save(update_fields=['progress_data', 'status', 'error_message', 'lease_expires_at', 'update_time'])
        return True

    @staticmethod
    def cleanup_success_matches_lease(lease, execution_id):
        return ExecutorTask.objects.select_for_update().filter(
            id=lease.task_id, task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value,
            business_id=execution_id, status=ExecutorTaskStatusEnum.SUCCESS.value,
            progress_data__claim_token=lease.token, progress_data__generation=lease.generation,
        ).exists()

    @classmethod
    @transaction.atomic
    def expire_inline_cleanup_tasks(cls):
        from src.apps.data_factory.enums.cleanup import DataFactoryCleanupModeEnum
        now = timezone.now()
        tasks = list(ExecutorTask.objects.select_for_update(skip_locked=True).filter(
            task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value,
            payload__mode=DataFactoryCleanupModeEnum.SYNCHRONOUS.value,
            status=ExecutorTaskStatusEnum.RUNNING.value, lease_expires_at__lte=now,
        ).order_by('id')[:100])
        for task in tasks:
            from src.apps.data_factory.exceptions import DATA_FACTORY_CLEANUP_INTERRUPTED
            from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue
            progress = dict(task.progress_data) if isinstance(task.progress_data, dict) else {}
            message = (f'同步清理任务 {task.id} 未在租约到期时间 {task.lease_expires_at.isoformat()} 前续约，平台无法确认执行进程是否仍在运行。'
                       f'请管理员核查工厂执行 {task.business_id} 的实际数据和清理明细；不会自动重放删除，未确认项仍须补清并验证')
            progress['infrastructure_issues'] = [DatasourceInfrastructureIssue(
                code=DATA_FACTORY_CLEANUP_INTERRUPTED.code,
                message=message).model_dump(mode='json')]
            task.progress_data = progress
            task.status = ExecutorTaskStatusEnum.FAILED.value
            task.error_code = ExecutorTaskErrorCodeEnum.DATA_FACTORY_CLEANUP_FAILED.value
            task.error_message = message
            task.finished_at = now
            task.lease_expires_at = None
            task.save(update_fields=['status', 'error_code', 'error_message', 'finished_at',
                                     'lease_expires_at', 'progress_data', 'update_time'])
        return [task.business_id for task in tasks]

    @classmethod
    def policy(cls, task_type: str) -> ExecutorTaskPolicy:
        return cls.POLICIES.get(str(task_type), cls.DEFAULT_POLICY)

    @classmethod
    def create(
            cls,
            *,
            task_type: str,
            created_by: User | int | None,
            executor_mode: str,
            payload: dict | BaseModel,
            business_type: str,
            business_id: int | None = None,
            executor_user: User | int | str | None = None,
            workspace_id: str | None = None,
            message_key: str | None = None,
            schedule_timeout_seconds: int | None = None,
            execution_timeout_seconds: int | None = None,
            target_executor_connection: SocketConnection | int | None = None,
    ) -> ExecutorTask:
        cls._validate_task_type(task_type)
        cls._validate_executor_mode(executor_mode)
        normalized_payload = cls.normalize_json(payload, cls.MAX_PAYLOAD_BYTES,
                                                EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)
        creator = cls._resolve_user(created_by)
        assigned_user = cls._resolve_user(executor_user)
        if executor_mode == ExecutorModeEnum.SELF.value:
            assigned_user = creator
        if executor_mode in {
            ExecutorModeEnum.SELF.value,
            ExecutorModeEnum.SPECIFIED.value,
            ExecutorModeEnum.WORKSPACE.value,
        } and assigned_user is None:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_USER_EXECUTION_NOT_FOUND)

        policy = cls.policy(task_type)
        schedule_seconds = (
            policy.schedule_timeout_seconds
            if schedule_timeout_seconds is None
            else max(0, int(schedule_timeout_seconds))
        )
        execution_seconds = (
            cls._configured_execution_timeout_seconds(
                task_type,
                policy.execution_timeout_seconds,
            )
            if execution_timeout_seconds is None
            else max(1, int(execution_timeout_seconds))
        )
        now = timezone.now()
        target_connection_id = (
            target_executor_connection.id
            if isinstance(target_executor_connection, SocketConnection)
            else target_executor_connection
        )
        target_connection = (
            SocketConnection.objects.filter(id=target_connection_id).first()
            if target_connection_id else None
        )
        connection = None if task_type == ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value else cls._available_connection(
            executor_mode,
            assigned_user,
            target_connection,
        )
        if connection is not None or task_type == ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value:
            status = ExecutorTaskStatusEnum.PENDING.value
            error_code = None
            error_message = None
        elif schedule_seconds > 0:
            status = ExecutorTaskStatusEnum.WAITING_EXECUTOR.value
            error_code = None
            error_message = None
        else:
            status = ExecutorTaskStatusEnum.FAILED.value
            offline_errors = {
                ExecutorModeEnum.SELF.value: (
                    "SELF_EXECUTOR_OFFLINE",
                    "本人执行器未连接，请先登录执行器或选择公共执行器",
                ),
                ExecutorModeEnum.PUBLIC.value: (
                    "NO_PUBLIC_EXECUTOR",
                    "当前没有可用的公共执行器",
                ),
                ExecutorModeEnum.SPECIFIED.value: (
                    "SPECIFIED_EXECUTOR_OFFLINE",
                    "指定执行器未连接，请检查执行器状态",
                ),
                ExecutorModeEnum.WORKSPACE.value: (
                    "WORKSPACE_EXECUTOR_OFFLINE",
                    "实时工作区绑定的执行器未连接，请重新连接工作区",
                ),
            }
            error_code, error_message = offline_errors[str(executor_mode)]

        values = {
            "task_type": str(task_type),
            "status": status,
            "created_by": creator,
            "executor_user": assigned_user,
            "executor_connection": None,
            "target_executor_connection_id": target_connection_id,
            "executor_mode": str(executor_mode),
            "business_type": str(business_type),
            "business_id": business_id,
            "workspace_id": str(workspace_id) if workspace_id else None,
            "payload": normalized_payload,
            "progress_data": {},
            "error_code": error_code,
            "error_message": error_message,
            "available_at": now,
            "schedule_deadline": now + timedelta(seconds=schedule_seconds) if schedule_seconds else None,
            # 创建阶段的最终截止时间需要覆盖“等待调度 + 实际执行”两段时间；
            # 真正开始执行时会基于当前时间重新计算执行截止时间。
            "expired_at": now + timedelta(seconds=schedule_seconds + execution_seconds),
            "finished_at": now if status == ExecutorTaskStatusEnum.FAILED.value else None,
        }
        try:
            with transaction.atomic():
                return ExecutorTask.objects.create(message_key=message_key, **values)
        except IntegrityError:
            if not message_key:
                raise
            return ExecutorTask.objects.get(message_key=message_key)

    @staticmethod
    def _configured_execution_timeout_seconds(
            task_type: str,
            default_seconds: int,
    ) -> int:
        from src.apps.system.services.configuration.system_config import SystemConfigService

        return SystemConfigService.get_executor_execution_timeout_seconds(
            task_type,
            default_seconds=default_seconds,
        )

    @classmethod
    def claim(
            cls,
            *,
            connection_id: str | None,
            username: str,
            capacity: int = 1,
            supported_task_types: list[str] | None = None,
            protocol_versions: dict[str, int] | None = None,
            capability_capacities: dict[str, int] | None = None,
            task_type_capacities: dict[str, int] | None = None,
    ) -> list[ExecutorTask]:
        for attempt in range(cls.DEADLOCK_MAX_ATTEMPTS):
            try:
                return cls._claim_once(
                    connection_id=connection_id,
                    username=username,
                    capacity=capacity,
                    supported_task_types=supported_task_types,
                    protocol_versions=protocol_versions,
                    capability_capacities=capability_capacities,
                    task_type_capacities=task_type_capacities,
                )
            except OperationalError as error:
                if not cls._is_mysql_deadlock(error) or attempt + 1 >= cls.DEADLOCK_MAX_ATTEMPTS:
                    raise
                delay = (
                        cls.DEADLOCK_BASE_DELAY_SECONDS * (2 ** attempt)
                        + random.uniform(0, cls.DEADLOCK_BASE_DELAY_SECONDS)
                )
                log.system.warning(
                    '执行器领取任务遇到数据库死锁，准备重试：'
                    f'attempt={attempt + 1}, delay={delay:.3f}s'
                )
                time.sleep(delay)
        return []

    @classmethod
    @transaction.atomic
    def _claim_once(
            cls,
            *,
            connection_id: str | None,
            username: str,
            capacity: int = 1,
            supported_task_types: list[str] | None = None,
            protocol_versions: dict[str, int] | None = None,
            capability_capacities: dict[str, int] | None = None,
            task_type_capacities: dict[str, int] | None = None,
    ) -> list[ExecutorTask]:
        connection = cls._require_connection(connection_id, username)
        if SocketConnectionService.is_draining(connection.connection_id):
            return []
        SocketConnectionService.update_capabilities(
            connection.connection_id,
            supported_task_types or [],
            protocol_versions or {},
            capability_capacities or {},
        )
        now = timezone.now()
        supported = [str(item) for item in (supported_task_types or []) if item]
        eligible = Q(executor_user_id=connection.user_id)
        if connection.is_open:
            eligible |= Q(
                executor_mode=ExecutorModeEnum.PUBLIC.value,
                executor_user_id__isnull=True,
            )
        queryset = (
            ExecutorTask.objects.select_for_update(skip_locked=True)
            .exclude(task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value)
            .filter(
                status__in=[
                    ExecutorTaskStatusEnum.PENDING.value,
                    ExecutorTaskStatusEnum.WAITING_EXECUTOR.value,
                ],
                available_at__lte=now,
                expired_at__gt=now,
            )
            .filter(eligible)
            .filter(
                Q(target_executor_connection__isnull=True)
                | Q(target_executor_connection=connection)
            )
        )
        if supported:
            queryset = queryset.filter(task_type__in=supported)
        available_by_type = {
            str(key): max(0, int(value))
            for key, value in (task_type_capacities or {}).items()
        }
        unavailable_types = [key for key, value in available_by_type.items() if value <= 0]
        if unavailable_types:
            queryset = queryset.exclude(task_type__in=unavailable_types)
        candidates = list(queryset.order_by("id")[: min(max(1, int(capacity)) * 3, 60)])
        versions = {str(key): int(value) for key, value in (protocol_versions or {}).items()}
        claimed_by_type: dict[str, int] = {}
        tasks = []
        for task in candidates:
            if not cls._protocol_supported(task, versions):
                continue
            if task.task_type in available_by_type:
                if claimed_by_type.get(task.task_type, 0) >= available_by_type[task.task_type]:
                    continue
            if task.executor_mode == ExecutorModeEnum.PUBLIC.value:
                if not cls._reserve_public_slot(task, connection):
                    continue
            tasks.append(task)
            claimed_by_type[task.task_type] = claimed_by_type.get(task.task_type, 0) + 1
            if len(tasks) >= min(max(1, int(capacity)), 20):
                break
        if not tasks:
            return []
        lease_until = now + timedelta(seconds=max(cls.policy(item.task_type).lease_seconds for item in tasks))
        task_ids = [item.id for item in tasks]
        ExecutorTask.objects.filter(id__in=task_ids).update(
            status=ExecutorTaskStatusEnum.CLAIMED.value,
            executor_user=connection.user,
            executor_connection=connection,
            lease_expires_at=lease_until,
            error_code=None,
            error_message=None,
            update_time=now,
        )
        for item in tasks:
            item.status = ExecutorTaskStatusEnum.CLAIMED.value
            item.executor_user = connection.user
            item.executor_connection = connection
            item.lease_expires_at = lease_until
        return tasks

    @staticmethod
    def _is_mysql_deadlock(error: OperationalError) -> bool:
        return bool(error.args) and error.args[0] == 1213

    @classmethod
    def mark_running(cls, task_id: int, connection_id: str, username: str) -> ExecutorTask:
        task = cls._owned_active_task(task_id, connection_id, username)
        now = timezone.now()
        if task.cancel_requested_at:
            return cls._finish(task, ExecutorTaskStatusEnum.CANCELLED.value, "cancelled", "任务已取消")
        if task.status not in {
            ExecutorTaskStatusEnum.CLAIMED.value,
            ExecutorTaskStatusEnum.RUNNING.value,
        }:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        # 自定义运行超时没有单独占字段；创建时 expired_at 与调度截止时间的差值
        # 就是本任务的运行预算。开始执行时平移该预算，不能退回任务类型默认值。
        timeout_origin = task.schedule_deadline or task.create_time
        execution_seconds = max(1, int((task.expired_at - timeout_origin).total_seconds()))
        task.status = ExecutorTaskStatusEnum.RUNNING.value
        task.started_at = task.started_at or now
        task.expired_at = now + timedelta(seconds=execution_seconds)
        task.lease_expires_at = now + timedelta(seconds=cls.policy(task.task_type).lease_seconds)
        task.save(update_fields=["status", "started_at", "expired_at", "lease_expires_at", "update_time"])
        cls._set_public_task_running(task, True)
        return task

    @classmethod
    def heartbeat(cls, task_id: int, connection_id: str, username: str) -> ExecutorTask:
        task = cls._owned_active_task(task_id, connection_id, username)
        if task.status not in {
            ExecutorTaskStatusEnum.CLAIMED.value,
            ExecutorTaskStatusEnum.RUNNING.value,
        }:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        task.lease_expires_at = timezone.now() + timedelta(seconds=cls.policy(task.task_type).lease_seconds)
        task.save(update_fields=["lease_expires_at", "update_time"])
        return task

    @classmethod
    def update_progress(
            cls,
            task_id: int,
            connection_id: str,
            username: str,
            progress: dict | BaseModel,
    ) -> ExecutorTask:
        task = cls.heartbeat(task_id, connection_id, username)
        task.progress_data = cls.normalize_json(progress, cls.MAX_PAYLOAD_BYTES,
                                                EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)
        task.save(update_fields=["progress_data", "update_time"])
        return task

    @classmethod
    def complete(cls, *, task_id, connection_id, username, success, result_data=None,
                 error_code=None, error_message=None, attempt=0):
        values = dict(task_id=task_id, connection_id=connection_id, username=username, success=success,
                      result_data=result_data, error_code=error_code, error_message=error_message, attempt=attempt)
        task = ExecutorTask.objects.filter(id=task_id, executor_user__username=username,
                                           retry_count=int(attempt)).first()
        cleanup_error_code = ExecutorTaskErrorCodeEnum.DATA_FACTORY_CLEANUP_FAILED.value
        if task is not None and task.status == ExecutorTaskStatusEnum.FAILED.value and task.error_code == cleanup_error_code:
            return task
        if (task is None or task.task_type not in (ExecutorTaskTypeEnum.UI_CASE.value, ExecutorTaskTypeEnum.UI_CASE_STEP.value)
                or task.status not in (ExecutorTaskStatusEnum.RUNNING.value, ExecutorTaskStatusEnum.CLAIMED.value)):
            return cls._complete(**values)
        if connection_id and not ExecutorTask.objects.filter(
                id=task.id, executor_connection__connection_id=connection_id).exists():
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        normalized = cls.normalize_json(result_data or {}, cls.MAX_RESULT_BYTES,
                                         EXECUTOR_TASK_EXECUTOR_TASK_RESULT_EXECUTION_INVALID)
        arguments = (task.payload or {}).get('func_args') or {}
        expected_ids = arguments.get('data_factory_auto_cleanup_execution_ids') or []
        expected_case_id = arguments.get('case_id') or arguments.get('id') or task.business_id
        if not isinstance(normalized, dict) or normalized.get('id') != expected_case_id:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_RESULT_EXECUTION_INVALID)
        normalized['data_factory_auto_cleanup_execution_ids'] = expected_ids
        values['result_data'] = normalized
        if not expected_ids:
            return cls._complete(**values)
        from src.apps.auto_ui.services.reporting.test_report_writing import TestReportWriting
        from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
        last_pulse = [0.0]

        def pulse():
            now = timezone.now()
            if time.monotonic() - last_pulse[0] < 5:
                return
            updated = ExecutorTask.objects.filter(
                id=task.id, retry_count=int(attempt), executor_user_id=task.executor_user_id,
                status__in=[ExecutorTaskStatusEnum.CLAIMED.value, ExecutorTaskStatusEnum.RUNNING.value],
                expired_at__gt=now, cancel_requested_at__isnull=True,
            ).update(lease_expires_at=now + timedelta(seconds=cls.policy(task.task_type).lease_seconds), update_time=now)
            if updated != 1:
                raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
            last_pulse[0] = time.monotonic()

        from src.apps.test_center.enums import TestCaseTypeEnum
        with DataFactoryCleanupScheduleService.parent_wait(pulse), DataFactoryCleanupScheduleService.report_scope(
                arguments.get('test_suite_details'), suite_id=arguments.get('test_suite_id'),
                case_id=expected_case_id, case_type=TestCaseTypeEnum.UI.value):
            normalized, failures = TestReportWriting.prepare_factory_result(normalized, expected_ids)
        values['result_data'] = normalized
        if failures:
            values.update(success=False, error_code=cleanup_error_code, error_message=normalized.get('error_message'))
        with TestReportWriting.prepared_cleanup_scope(expected_ids):
            return cls._complete(**values)

    @classmethod
    @transaction.atomic
    def _complete(
            cls,
            *,
            task_id: int,
            connection_id: str | None,
            username: str,
            success: bool,
            result_data: dict | list | None = None,
            error_code: str | None = None,
            error_message: str | None = None,
            attempt: int = 0,
    ) -> ExecutorTask:
        expected_status = (
            ExecutorTaskStatusEnum.CANCELLED.value
            if error_code == "cancelled"
            else ExecutorTaskStatusEnum.SUCCESS.value
            if success
            else ExecutorTaskStatusEnum.FAILED.value
        )
        existing = ExecutorTask.objects.filter(
            id=task_id,
            executor_user__username=username,
        ).first()
        if existing is not None and existing.status in ExecutorTaskStatusEnum.terminal_values():
            # 执行器可能在结果首次提交后、收到HTTP响应前断线。重连后重复提交
            # 终态必须按幂等成功处理，不能要求仍持有旧 connection 租约。
            if existing.status == expected_status:
                return existing
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        # 最终结果可能在服务端已保存、HTTP响应返回前断线。执行器重连后使用
        # Outbox 补交，此时旧 connection 已离线；attempt 仍可证明这是当前领取批次，
        # 同时避免租约恢复后的旧结果覆盖新一轮执行。
        active_query = ExecutorTask.objects.select_related("executor_user").filter(
            id=task_id,
            executor_user__username=username,
            retry_count=int(attempt),
            status__in=[
                ExecutorTaskStatusEnum.CLAIMED.value,
                ExecutorTaskStatusEnum.RUNNING.value,
            ],
        )
        if connection_id:
            active_query = active_query.filter(
                executor_connection__connection_id=connection_id,
            )
        task = active_query.first()
        if task is None:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        normalized_result = cls.normalize_json(
            result_data if result_data is not None else {},
            cls.MAX_RESULT_BYTES,
            EXECUTOR_TASK_EXECUTOR_TASK_RESULT_EXECUTION_INVALID,
        )
        task.result_data = normalized_result
        if error_code == "cancelled":
            if task.task_type == ExecutorTaskTypeEnum.PYTEST_EXECUTION.value:
                with transaction.atomic():
                    cls._project_business_result(
                        task,
                        normalized_result,
                        success=False,
                        error_message=error_message or "用户已取消任务",
                    )
            return cls._finish(
                task,
                ExecutorTaskStatusEnum.CANCELLED.value,
                error_code,
                error_message or "用户已取消任务",
            )
        try:
            # 业务执行失败同样包含失败节点、截图、定位明细等必须持久化的结果，
            # 因此不能只在 success=True 时投影。
            # 独立保存点保证投影中的数据库异常可以完整回滚，同时仍允许外层事务
            # 把任务落为可查询的 result_projection_failed 终态。
            with transaction.atomic():
                cls._project_business_result(
                    task,
                    normalized_result,
                    success=success,
                    error_message=error_message,
                )
        except Exception as error:
            # 任务事实与业务投影必须形成同一个可查询终态。投影异常不能让执行器
            # 永久重试一个实际已执行完成的任务，也不能留下 running 状态。
            from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
            reference = DatasourceInfrastructureService.log_reference(error, 'executor_result_projection')
            log.system.error('执行器任务业务结果投影失败 task_id=%s reference=%s', task.id, reference)
            return cls._finish(
                task,
                ExecutorTaskStatusEnum.FAILED.value,
                "result_projection_failed",
                f"执行任务 {task.id} 已返回结果，但平台保存报告失败。请管理员按关联编号 {reference} 检查业务结果投影日志，不要直接重复执行",
            )
        return cls._finish(
            task,
            ExecutorTaskStatusEnum.SUCCESS.value if success else ExecutorTaskStatusEnum.FAILED.value,
            error_code,
            error_message,
        )

    @staticmethod
    def _project_business_result(
            task: ExecutorTask,
            result_data: dict | list,
            *,
            success: bool = True,
            error_message: str | None = None,
    ) -> None:
        """在任务形成终态前同步更新业务投影，避免任务结果与最新快照产生竞态。"""
        if not isinstance(result_data, dict):
            return
        if (
                task.task_type == ExecutorTaskTypeEnum.API_EXECUTION.value
                and task.business_type == ServerApiCommandEnum.API_CASE.value
                and task.business_id is not None
        ):
            from mangotools.enums import TaskEnum
            from src.apps.auto_api.services.execution.cases.run_status import ApiCaseRunStatusService

            try:
                status = int(result_data.get("status"))
            except (TypeError, ValueError):
                status = TaskEnum.SUCCESS.value if success else TaskEnum.FAIL.value
            if status not in {
                TaskEnum.FAIL.value,
                TaskEnum.SUCCESS.value,
                TaskEnum.WARNING.value,
            }:
                status = TaskEnum.SUCCESS.value if success else TaskEnum.FAIL.value
            ApiCaseRunStatusService.project_status(task.business_id, status)
            return
        if task.task_type == ExecutorTaskTypeEnum.PYTEST_EXECUTION.value:
            from mangotools.contracts import PytestExecutionResult
            from src.apps.auto_pytest.services.reporting.test_report_writing import PtestTestReportWriting
            from mangotools.enums import StatusEnum

            payload = task.payload if isinstance(task.payload, dict) else {}
            func_args = payload.get("func_args") if isinstance(payload.get("func_args"), dict) else {}
            case_id = result_data.get("id") or func_args.get("id")
            case_name = result_data.get("name") or func_args.get("name") or f"Pytest Case #{case_id}"
            status = result_data.get("status")
            if status is None:
                status = StatusEnum.SUCCESS.value if success else StatusEnum.FAIL.value
            case_result_data = result_data.get("result_data")
            if case_result_data is None and not success:
                case_result_data = [{
                    "name": case_name,
                    "status": StatusEnum.FAIL.value,
                    "statusDetails": {"message": error_message or "Pytest 执行失败"},
                }]
            projected_result = PytestExecutionResult(
                dispatch_id=result_data.get("dispatch_id") or func_args.get("dispatch_id"),
                source_snapshot=(
                    result_data.get("source_snapshot")
                    if isinstance(result_data.get("source_snapshot"), dict)
                    else func_args.get("source_snapshot")
                ),
                id=case_id,
                name=case_name,
                status=status,
                result_data=case_result_data,
            )
            PtestTestReportWriting.update_pytest_test_case.__wrapped__(
                PtestTestReportWriting,
                projected_result,
            )
            return
        if task.task_type == ExecutorTaskTypeEnum.CONFIG_COMMAND.value:
            payload = task.payload if isinstance(task.payload, dict) else {}
            func_name = payload.get("func_name")
            if func_name not in {
                ServerToolsCommandEnum.GET_ACTUATOR_CONFIG.value,
                ServerToolsCommandEnum.UPDATE_ACTUATOR_CONFIG.value,
            }:
                return
            # 旧执行器对这两个命令只发 WebSocket 回调并返回空结果，不能把
            # 空配置误投影成读取成功；新执行器会通过统一任务结果返回完整快照。
            if not isinstance(result_data.get("config"), dict):
                return
            func_args = (
                payload.get("func_args")
                if isinstance(payload.get("func_args"), dict)
                else {}
            )
            projected_result = dict(result_data)
            projected_result["request_id"] = (
                    projected_result.get("request_id") or func_args.get("request_id")
            )
            executor_user = getattr(task, "executor_user", None)
            projected_result["username"] = (
                    projected_result.get("username") or getattr(executor_user, "username", None)
            )

            from src.apps.system.services.socket_link.consumer.system import SystemConsumer

            if func_name == ServerToolsCommandEnum.GET_ACTUATOR_CONFIG.value:
                SystemConsumer.save_actuator_config_snapshot(projected_result)
            else:
                SystemConsumer.save_actuator_config_save_result(projected_result)
            return
        if task.task_type in {
            ExecutorTaskTypeEnum.ELEMENT_CHECK.value,
            ExecutorTaskTypeEnum.ELEMENT_DEEP_CHECK.value,
        } and result_data.get("element_id"):
            from src.apps.auto_ui.services.elements.ai.element_ai_service import ElementAiService

            ElementAiService.save_check_result(result_data)
            return
        if task.task_type == ExecutorTaskTypeEnum.AUTH_CAPTURE.value:
            config_id = result_data.get("config_id")
            cache_data = result_data.get("cache_data")
            if config_id and isinstance(cache_data, dict):
                from src.apps.auto_ui.services.authentication.ui_auth import UiAuthManager

                UiAuthManager.save_auto_auth_cache(config_id, cache_data)
            return
        if task.task_type in {
            ExecutorTaskTypeEnum.PAGE_STEP_DEBUG.value,
            ExecutorTaskTypeEnum.PAGE_STEP_NODE_DEBUG.value,
        }:
            from src.apps.system.services.socket_link.consumer.ui import UIConsumer

            UIConsumer.save_page_steps_result(result_data)
            return
        if task.task_type in {
            ExecutorTaskTypeEnum.UI_CASE.value,
            ExecutorTaskTypeEnum.UI_CASE_STEP.value,
        }:
            from src.apps.system.services.socket_link.consumer.ui import UIConsumer

            UIConsumer.save_test_case_result(result_data)

    @classmethod
    def _project_terminal_failure(cls, task: ExecutorTask, message: str) -> None:
        try:
            from src.apps.task_center.services.execution.status_reconciliation import (
                ExecutionStatusProjectionService,
            )

            ExecutionStatusProjectionService.project(task, force_failure=True)
        except Exception as error:
            log.system.error(
                f"执行器任务失败终态投影失败：task_id={task.id}，"
                f"message={message}，error={error}"
            )

    @classmethod
    def cancel(cls, task_id: int, user_id: int) -> ExecutorTask:
        task = cls.get_for_user(task_id, user_id)
        if task.task_type == ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        if task.status in ExecutorTaskStatusEnum.terminal_values():
            return task
        now = timezone.now()
        task.cancel_requested_at = now
        update_fields = ["cancel_requested_at", "update_time"]
        if task.status in {
            ExecutorTaskStatusEnum.WAITING_EXECUTOR.value,
            ExecutorTaskStatusEnum.PENDING.value,
        }:
            task.status = ExecutorTaskStatusEnum.CANCELLED.value
            task.finished_at = now
            task.error_code = ExecutorTaskErrorCodeEnum.CANCELLED.value
            task.error_message = "用户已取消任务"
            update_fields.extend(["status", "finished_at", "error_code", "error_message"])
        task.save(update_fields=update_fields)
        if task.status == ExecutorTaskStatusEnum.CANCELLED.value:
            cls._project_terminal_failure(task, task.error_message)
        return task

    @classmethod
    def recover_expired(cls, batch_size: int | None = None) -> dict[str, int]:
        batch_size = max(1, min(int(batch_size or cls.RECOVERY_BATCH_SIZE), 500))
        now = timezone.now()
        public_tasks = []
        terminal_failures: list[tuple[ExecutorTask, str]] = []

        with transaction.atomic():
            cancelled_tasks = list(
                ExecutorTask.objects.select_for_update(skip_locked=True).filter(
                    status__in=[
                        ExecutorTaskStatusEnum.CLAIMED.value,
                        ExecutorTaskStatusEnum.RUNNING.value,
                    ],
                    cancel_requested_at__isnull=False,
                ).filter(
                    Q(lease_expires_at__lte=now) | Q(expired_at__lte=now)
                ).exclude(task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value).order_by('id')[:batch_size]
            )
            cancelled_ids = [task.id for task in cancelled_tasks]
            cancelled = 0
            if cancelled_ids:
                cancelled = ExecutorTask.objects.filter(id__in=cancelled_ids).update(
                    status=ExecutorTaskStatusEnum.CANCELLED.value,
                    error_code=ExecutorTaskErrorCodeEnum.CANCELLED.value,
                    error_message="用户已取消任务",
                    finished_at=now,
                    lease_expires_at=None,
                    update_time=now,
                )
            for task in cancelled_tasks:
                if task.executor_mode == ExecutorModeEnum.PUBLIC.value:
                    public_tasks.append(task)
                terminal_failures.append((task, "用户已取消任务"))

        with transaction.atomic():
            waiting_timeout_tasks = list(
                ExecutorTask.objects.select_for_update(skip_locked=True).filter(
                    status__in=[
                        ExecutorTaskStatusEnum.WAITING_EXECUTOR.value,
                        ExecutorTaskStatusEnum.PENDING.value,
                    ],
                ).filter(
                    Q(schedule_deadline__isnull=False, schedule_deadline__lte=now)
                    | Q(schedule_deadline__isnull=True, expired_at__lte=now)
                ).exclude(task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value).order_by('id')[:batch_size]
            )
            waiting_timeout_ids = [task.id for task in waiting_timeout_tasks]
            waiting_timeout = 0
            if waiting_timeout_ids:
                waiting_timeout = ExecutorTask.objects.filter(id__in=waiting_timeout_ids).update(
                    status=ExecutorTaskStatusEnum.TIMEOUT.value,
                    error_code=ExecutorTaskErrorCodeEnum.SCHEDULE_TIMEOUT.value,
                    error_message="等待可用执行器超过调度截止时间，用例尚未开始。请检查执行器在线状态、版本匹配及任务占用",
                    finished_at=now,
                    update_time=now,
                )
            terminal_failures.extend(
                (task, f"任务 {task.id} 等待可用执行器超过调度截止时间 {task.schedule_deadline or task.expired_at}，用例尚未开始。请检查执行器在线状态、版本匹配及任务占用")
                for task in waiting_timeout_tasks
            )

        with transaction.atomic():
            execution_timeout_tasks = list(
                ExecutorTask.objects.select_for_update(skip_locked=True).filter(
                    status__in=[
                        ExecutorTaskStatusEnum.CLAIMED.value,
                        ExecutorTaskStatusEnum.RUNNING.value,
                    ],
                    expired_at__lte=now,
                    cancel_requested_at__isnull=True,
                ).exclude(task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value).order_by('id')[:batch_size]
            )
            execution_timeout_ids = [task.id for task in execution_timeout_tasks]
            execution_timeout = 0
            if execution_timeout_ids:
                execution_timeout = ExecutorTask.objects.filter(id__in=execution_timeout_ids).update(
                    status=ExecutorTaskStatusEnum.TIMEOUT.value,
                    error_code=ExecutorTaskErrorCodeEnum.EXECUTION_TIMEOUT.value,
                    error_message="任务执行超过配置截止时间，最终结果未确认。请检查执行器日志及请求和清理状态，勿直接重复写入",
                    finished_at=now,
                    lease_expires_at=None,
                    update_time=now,
                )
            public_tasks.extend(
                task
                for task in execution_timeout_tasks
                if task.executor_mode == ExecutorModeEnum.PUBLIC.value
            )
            terminal_failures.extend(
                (task, f"任务 {task.id} 执行超过配置截止时间 {task.expired_at}，最终结果未确认。请检查执行器日志及请求和清理状态，勿直接重复写入")
                for task in execution_timeout_tasks
            )

        retried = 0
        interrupted = 0
        with transaction.atomic():
            lease_tasks = list(ExecutorTask.objects.select_for_update(skip_locked=True).filter(
                status__in=[ExecutorTaskStatusEnum.CLAIMED.value, ExecutorTaskStatusEnum.RUNNING.value],
                lease_expires_at__isnull=False,
                lease_expires_at__lte=now,
                expired_at__gt=now,
                cancel_requested_at__isnull=True,
            ).exclude(task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value).order_by('id')[:batch_size])
            for task in lease_tasks:
                if task.executor_mode == ExecutorModeEnum.PUBLIC.value:
                    public_tasks.append(copy(task))
                # 只完成领取、尚未进入 running 的任务没有产生页面副作用，可以直接
                # 释放租约重新领取，并且不消耗业务重试次数。
                if task.status == ExecutorTaskStatusEnum.CLAIMED.value and task.started_at is None:
                    task.status = (
                        ExecutorTaskStatusEnum.WAITING_EXECUTOR.value
                        if task.executor_mode in {
                            ExecutorModeEnum.SELF.value,
                            ExecutorModeEnum.SPECIFIED.value,
                            ExecutorModeEnum.WORKSPACE.value,
                        }
                        else ExecutorTaskStatusEnum.PENDING.value
                    )
                    task.executor_connection = None
                    if task.executor_mode == ExecutorModeEnum.PUBLIC.value:
                        task.executor_user = None
                    task.lease_expires_at = None
                    task.available_at = now
                    task.error_code = ExecutorTaskErrorCodeEnum.CLAIM_LEASE_RELEASED.value
                    task.error_message = "执行器领取后未开始，任务已释放并等待重新领取"
                    task.save()
                    retried += 1
                    continue
                policy = cls.policy(task.task_type)
                if task.retry_count < policy.max_retries:
                    task.status = ExecutorTaskStatusEnum.PENDING.value
                    task.retry_count += 1
                    task.executor_connection = None
                    if task.executor_mode == ExecutorModeEnum.PUBLIC.value:
                        # 公共任务的领取人只是本次租约归属；租约丢失后必须重新开放给
                        # 其他公共执行器，否则任务会永久黏在已失联用户上。
                        task.executor_user = None
                    task.lease_expires_at = None
                    task.available_at = now
                    task.error_code = ExecutorTaskErrorCodeEnum.LEASE_LOST_RETRYING.value
                    task.error_message = "执行器心跳中断，任务将重新领取"
                    retried += 1
                else:
                    task.status = ExecutorTaskStatusEnum.INTERRUPTED.value
                    task.finished_at = now
                    task.lease_expires_at = None
                    task.error_code = ExecutorTaskErrorCodeEnum.EXECUTOR_DISCONNECTED.value
                    task.error_message = "执行器连接中断，任务未完成"
                    terminal_failures.append((task, task.error_message))
                    interrupted += 1
                task.save()

        for task in public_tasks:
            cls._set_public_task_running(task, False)
        for task, message in terminal_failures:
            cls._project_terminal_failure(task, message)
        return {
            "cancelled": cancelled,
            "waiting_timeout": waiting_timeout,
            "execution_timeout": execution_timeout,
            "retried": retried,
            "interrupted": interrupted,
            "batch_size": batch_size,
        }

    @classmethod
    @transaction.atomic
    def set_connection_draining(
            cls,
            *,
            connection_id: str | None,
            username: str,
            draining: bool,
    ) -> SocketConnection:
        connection = cls._require_connection(connection_id, username)
        SocketConnectionService.set_draining(connection.connection_id, draining)
        if not draining:
            return connection
        now = timezone.now()
        tasks = list(ExecutorTask.objects.select_for_update().filter(
            executor_connection=connection,
            status=ExecutorTaskStatusEnum.CLAIMED.value,
            started_at__isnull=True,
        ))
        for task in tasks:
            task.status = (
                ExecutorTaskStatusEnum.WAITING_EXECUTOR.value
                if task.executor_mode in {
                    ExecutorModeEnum.SELF.value,
                    ExecutorModeEnum.SPECIFIED.value,
                    ExecutorModeEnum.WORKSPACE.value,
                }
                else ExecutorTaskStatusEnum.PENDING.value
            )
            task.executor_connection = None
            if task.executor_mode == ExecutorModeEnum.PUBLIC.value:
                task.executor_user = None
            task.lease_expires_at = None
            task.available_at = now
            task.error_code = ExecutorTaskErrorCodeEnum.EXECUTOR_DRAINING.value
            task.error_message = "执行器正在正常退出，未开始任务已释放"
            task.save()
        return connection

    @classmethod
    def get_for_user(cls, task_id: int, user_id: int) -> ExecutorTask:
        task = ExecutorTask.objects.select_related(
            "created_by", "executor_user", "executor_connection"
        ).filter(id=task_id).first()
        if task is None:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_EXECUTION_CLEANUP_NOT_FOUND)
        if task.created_by_id != int(user_id):
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_EXECUTION_ACCESS_DENIED)
        return task

    @classmethod
    def list_active_for_user(
            cls,
            user_id: int,
            *,
            business_type: str | None = None,
            business_id: int | None = None,
    ) -> list[ExecutorTask]:
        queryset = ExecutorTask.objects.select_related(
            "executor_user", "executor_connection"
        ).filter(
            created_by_id=user_id,
        ).exclude(status__in=ExecutorTaskStatusEnum.terminal_values())
        if business_type:
            queryset = queryset.filter(business_type=business_type)
        if business_id is not None:
            queryset = queryset.filter(business_id=business_id)
        return list(queryset.order_by("-id")[:100])

    @classmethod
    def serialize(cls, task: ExecutorTask, *, include_payload: bool = False) -> dict[str, Any]:
        data = {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "terminal": task.status in ExecutorTaskStatusEnum.terminal_values(),
            "executor_mode": task.executor_mode,
            "executor_username": getattr(task.executor_user, "username", None),
            "executor_connection_id": str(task.executor_connection.connection_id)
            if task.executor_connection_id
            else None,
            "business_type": task.business_type,
            "business_id": task.business_id,
            "workspace_id": task.workspace_id,
            "progress": task.progress_data or {},
            "result": task.result_data,
            "error_code": task.error_code,
            "error_message": task.error_message,
            "cancel_requested": task.cancel_requested_at is not None,
            "retry_count": task.retry_count,
            "create_time": cls._datetime_text(task.create_time),
            "update_time": cls._datetime_text(task.update_time),
            "started_at": cls._datetime_text(task.started_at),
            "finished_at": cls._datetime_text(task.finished_at),
            "schedule_deadline": cls._datetime_text(task.schedule_deadline),
            "expired_at": cls._datetime_text(task.expired_at),
        }
        if include_payload:
            data["payload"] = task.payload or {}
        return data

    @classmethod
    def claim_payload(cls, task: ExecutorTask) -> dict[str, Any]:
        return cls.serialize(task, include_payload=True)

    @classmethod
    def cleanup_history(cls, retention_days: int = 7, batch_size: int = 1000) -> int:
        from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
        from src.apps.data_factory.enums.cleanup import DataFactoryCleanupStatusEnum
        completed = DataFactoryQuerySelector.data_factory_execution().filter(
            Q(cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value)
            | Q(cleanup_status=DataFactoryCleanupStatusEnum.SKIPPED.value,
                datafactoryexecutionitem__isnull=True)).values('id')
        cutoff_time = timezone.now() - timedelta(days=retention_days)
        ids = list(
            ExecutorTask.objects.filter(
                ~Q(task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value) | Q(business_id__in=completed),
                finished_at__isnull=False,
                finished_at__lt=cutoff_time,
            ).order_by("id").values_list("id", flat=True)[:batch_size]
        )
        if not ids:
            return 0
        deleted, _ = ExecutorTask.objects.filter(id__in=ids).delete()
        return deleted

    @classmethod
    def normalize_json(cls, value: Any, max_bytes: int, error_message: ErrorDefinition) -> dict | list:
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        if not isinstance(value, (dict, list)):
            raise TaskCenterError(error_message)
        try:
            encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise TaskCenterError(error_message, error=str(error)) from error
        if len(encoded) > max_bytes:
            raise TaskCenterError(error_message)
        return value

    @staticmethod
    def _resolve_user(value: User | int | str | None) -> User | None:
        if value is None:
            return None
        if isinstance(value, User):
            return value
        queryset = User.objects.filter(id=value) if isinstance(value, int) else User.objects.filter(username=value)
        user = queryset.first()
        if user is None:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_USER_EXECUTION_NOT_FOUND)
        return user

    @staticmethod
    def _validate_task_type(task_type: str) -> None:
        if str(task_type) not in {item.value for item in ExecutorTaskTypeEnum}:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)

    @staticmethod
    def _validate_executor_mode(executor_mode: str) -> None:
        if str(executor_mode) not in {item.value for item in ExecutorModeEnum}:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_PARAMETER_EXECUTION_INVALID)

    @classmethod
    def _available_connection(
            cls,
            mode: str,
            user: User | None,
            target_connection: SocketConnection | None = None,
    ) -> SocketConnection | None:
        if target_connection is not None:
            online_ids = {item.id for item in SocketConnectionService.list_online_actuators()}
            if (
                    target_connection.id in online_ids
                    and not SocketConnectionService.is_draining(target_connection.connection_id)
            ):
                return target_connection
            return None
        if mode == ExecutorModeEnum.PUBLIC.value:
            return next((
                item for item in SocketConnectionService.list_online_actuators()
                if item.is_open
                   and not SocketConnectionService.is_draining(item.connection_id)
            ), None)
        if not user or not SocketConnectionService.is_actuator_online(user.id):
            return None
        connection = SocketConnectionService.get_current_actuator(user.id)
        if connection and SocketConnectionService.is_draining(connection.connection_id):
            return None
        return connection

    @staticmethod
    def _protocol_supported(task: ExecutorTask, protocol_versions: dict[str, int]) -> bool:
        if not protocol_versions:
            return True
        supported_version = protocol_versions.get(task.task_type, protocol_versions.get("*"))
        if supported_version is None:
            return False
        payload = task.payload if isinstance(task.payload, dict) else {}
        return int(payload.get("schema_version") or 1) <= int(supported_version)

    @classmethod
    def _require_connection(cls, connection_id: str | None, username: str) -> SocketConnection:
        queryset = SocketConnection.objects.select_related("user").filter(
            user__username=username,
            client_type=ClientTypeEnum.ACTUATOR.value,
            status=SocketConnectionStatusEnum.ONLINE.value,
            last_seen_at__gte=timezone.now() - timedelta(seconds=SocketConnectionService.ONLINE_TIMEOUT_SECONDS),
        )
        if connection_id:
            queryset = queryset.filter(connection_id=connection_id)
        connection = queryset.order_by("-last_seen_at", "-id").first()
        if connection is None:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_USER_EXECUTION_NOT_FOUND)
        return connection

    @classmethod
    def _owned_active_task(cls, task_id: int, connection_id: str | None, username: str) -> ExecutorTask:
        task = cls._owned_task(task_id, connection_id, username)
        if task.status in ExecutorTaskStatusEnum.terminal_values():
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        return task

    @classmethod
    def _owned_task(cls, task_id: int, connection_id: str | None, username: str) -> ExecutorTask:
        connection = cls._require_connection(connection_id, username)
        task = ExecutorTask.objects.filter(
            id=task_id,
            executor_connection=connection,
            executor_user__username=username,
        ).first()
        if task is None:
            raise TaskCenterError(EXECUTOR_TASK_EXECUTOR_TASK_STATUS_EXECUTION_INVALID)
        return task

    @staticmethod
    def _finish(task: ExecutorTask, status: str, error_code: str | None, error_message: str | None) -> ExecutorTask:
        task.status = status
        task.finished_at = timezone.now()
        task.lease_expires_at = None
        task.error_code = str(error_code)[:64] if error_code else None
        task.error_message = str(error_message)[: ExecutorTaskService.MAX_ERROR_LENGTH] if error_message else None
        task.save(update_fields=[
            "status", "result_data", "finished_at", "lease_expires_at",
            "error_code", "error_message", "update_time",
        ])
        ExecutorTaskService._set_public_task_running(task, False)
        transaction.on_commit(lambda: ExecutorTaskService._publish_finished_event(
            task_id=task.id,
            task_type=task.task_type,
            business_id=task.business_id,
            status=task.status,
        ))
        return task

    @staticmethod
    def _publish_finished_event(*, task_id: int, task_type: str, business_id: int | None, status: str) -> None:
        responses = executor_task_finished.send_robust(
            sender=ExecutorTask,
            task_id=task_id,
            task_type=task_type,
            business_id=business_id,
            status=status,
        )
        for receiver, result in responses:
            if isinstance(result, Exception):
                receiver_name = getattr(receiver, "__qualname__", repr(receiver))
                log.system.exception(
                    "执行器任务完成事件处理失败：receiver=%s task_id=%s",
                    receiver_name,
                    task_id,
                )

    @staticmethod
    def _reserve_public_slot(task: ExecutorTask, connection: SocketConnection) -> bool:
        if task.created_by_id is None:
            return False
        try:
            from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService

            ExecutorSlotLeaseService.acquire(
                user={
                    "id": task.created_by_id,
                    "username": getattr(task.created_by, "username", str(task.created_by_id)),
                },
                connection=connection,
                runtime_type=task.task_type,
                resource_id=task.business_id,
                workspace_id=task.workspace_id,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _set_public_task_running(task: ExecutorTask, running: bool) -> None:
        if task.executor_mode != ExecutorModeEnum.PUBLIC.value or not task.executor_connection_id:
            return
        try:
            from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService

            occupancy = ExecutorSlotLeaseService.occupancy(task.executor_connection)
            slot = next(
                (
                    item for item in occupancy.get("users", [])
                    if int(item.get("user_id") or 0) == int(task.created_by_id or 0)
                ),
                None,
            )
            # occupancy 的精简用户数据不包含 slot_id，按 user_id touch 后取得完整槽位。
            if slot:
                full_slot = ExecutorSlotLeaseService.touch(
                    str(task.executor_connection.connection_id),
                    user_id=task.created_by_id,
                )
                if full_slot:
                    ExecutorSlotLeaseService.set_running(
                        str(task.executor_connection.connection_id),
                        full_slot["slot_id"],
                        running,
                        execution_id=str(task.id),
                    )
        except Exception:
            # 槽位只是公共执行器容量保护；任务终态不能因缓存短暂不可用而回滚。
            return

    @staticmethod
    def _datetime_text(value) -> str | None:
        if not value:
            return None
        normalized = timezone.localtime(value) if timezone.is_aware(value) else value
        return normalized.strftime("%Y-%m-%d %H:%M:%S")
